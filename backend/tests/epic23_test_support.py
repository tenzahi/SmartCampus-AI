import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
import redis
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.engine import make_url
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.models import Conversation, ConversationProfile, GuestSession, Message, User
from app.db.redis_client import get_redis
from app.db.session import get_db
from app.main import app


@compiles(INET, "sqlite")
def _compile_inet_sqlite(type_, compiler, **kwargs):
    return "VARCHAR(45)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kwargs):
    return "JSON"


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kwargs):
    return "CHAR(36)"


@dataclass
class MemoryRedis:
    values: dict[str, str] = field(default_factory=dict)
    lists: dict[str, list[str]] = field(default_factory=dict)

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.values[key] = value

    def rpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).append(value)

    def ltrim(self, key: str, start: int, end: int) -> None:
        values = self.lists.get(key, [])
        self.lists[key] = values[start:] if end == -1 else values[start : end + 1]

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        values = self.lists.get(key, [])
        return values[start:] if end == -1 else values[start : end + 1]

    def expire(self, key: str, ttl: int) -> bool:
        return key in self.values or key in self.lists


@dataclass
class RedisHarness:
    client: "NamespacedRedis"
    raw_client: redis.Redis
    conversation_ids: list[str] = field(default_factory=list)
    keys: set[str] = field(default_factory=set)

    def track(self, conversation_id: str) -> None:
        self.conversation_ids.append(conversation_id)

    def track_key(self, key: str) -> None:
        self.keys.add(key)


class NamespacedRedis:
    def __init__(self, client: redis.Redis, prefix: str):
        self._client = client
        self._prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str):
        return self._client.get(self._key(key))

    def set(self, key: str, value: str, ex: int | None = None):
        return self._client.set(self._key(key), value, ex=ex)

    def setex(self, key: str, ttl: int, value: str):
        return self._client.setex(self._key(key), ttl, value)

    def rpush(self, key: str, value: str):
        return self._client.rpush(self._key(key), value)

    def ltrim(self, key: str, start: int, end: int):
        return self._client.ltrim(self._key(key), start, end)

    def lrange(self, key: str, start: int, end: int):
        return self._client.lrange(self._key(key), start, end)

    def expire(self, key: str, ttl: int):
        return self._client.expire(self._key(key), ttl)

    def ttl(self, key: str):
        return self._client.ttl(self._key(key))

    def delete(self, *keys: str):
        return self._client.delete(*(self._key(key) for key in keys))

@pytest.fixture
def sqlite_sessions():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # PostgreSQL JSONB defaults are not valid SQLite SQL; adjust only during
    # this isolated test schema creation, then restore the application metadata.
    json_defaults = []
    for model in (ConversationProfile, Message):
        column = (
            model.__table__.c.profile_json
            if model is ConversationProfile
            else model.__table__.c["metadata"]
        )
        json_defaults.append((column, column.server_default))
        column.server_default = text("'{}'")
    try:
        Base.metadata.create_all(engine)
    finally:
        for column, default in json_defaults:
            column.server_default = default

    @event.listens_for(Conversation, "before_insert")
    def _assign_uuid(_mapper, _connection, target):
        if target.id is None:
            target.id = uuid.uuid4()

    @event.listens_for(GuestSession, "load")
    def _restore_utc_timezone(_target, _context):
        if _target.expires_at is not None and _target.expires_at.tzinfo is None:
            _target.expires_at = _target.expires_at.replace(tzinfo=timezone.utc)

    factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield factory
    finally:
        event.remove(Conversation, "before_insert", _assign_uuid)
        event.remove(GuestSession, "load", _restore_utc_timezone)
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def fake_redis():
    return MemoryRedis()


@pytest.fixture
def real_redis():
    test_url = os.environ.get("TEST_REDIS_URL")
    if not test_url:
        pytest.fail("TEST_REDIS_URL requis; aucun fallback Redis n'est autorisé.")
    if os.environ.get("TESTING", "").lower() != "true":
        pytest.fail("TESTING=true requis pour utiliser Redis de test.")

    test_parts = urlsplit(test_url)
    test_identity = (
        test_parts.hostname,
        test_parts.port or 6379,
        (test_parts.path or "/0").strip("/") or "0",
    )
    dev_parts = urlsplit(settings.redis_url)
    dev_identity = (
        dev_parts.hostname,
        dev_parts.port or 6379,
        (dev_parts.path or "/0").strip("/") or "0",
    )
    if test_identity != ("127.0.0.1", 6380, "0") or test_identity == dev_identity:
        pytest.fail(
            "TEST_REDIS_URL doit cibler exclusivement 127.0.0.1:6380/0."
        )

    client = redis.Redis.from_url(test_url, decode_responses=True)
    try:
        client.ping()
    except redis.RedisError as exc:
        client.close()
        pytest.fail(f"Redis de test indisponible sur 127.0.0.1:6380: {exc}")

    harness = RedisHarness(
        client=NamespacedRedis(client, "epic23:test:"),
        raw_client=client,
    )
    try:
        yield harness
    finally:
        keys = []
        for conversation_id in harness.conversation_ids:
            keys.extend(
                [
                    f"conv:{conversation_id}:messages",
                    f"conv:{conversation_id}:profile",
                ]
            )
        keys.extend(harness.keys)
        if keys:
            harness.client.delete(*keys)
        client.close()


@pytest.fixture
def test_postgres_engine():
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        pytest.fail("TEST_DATABASE_URL requis; aucun fallback PostgreSQL n'est autorisé.")
    if os.environ.get("TESTING", "").lower() != "true":
        pytest.fail("TESTING=true requis pour utiliser PostgreSQL de test.")

    try:
        parsed_url = make_url(test_url)
    except Exception as exc:
        pytest.fail(f"TEST_DATABASE_URL est invalide: {exc}")
    if (
        parsed_url.get_backend_name() != "postgresql"
        or parsed_url.host != "127.0.0.1"
        or parsed_url.port != 5435
        or parsed_url.database != "smartcampus_test"
    ):
        pytest.fail(
            "TEST_DATABASE_URL doit cibler PostgreSQL sur "
            "127.0.0.1:5435/smartcampus_test."
        )

    engine = create_engine(test_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            database_name = connection.scalar(text("SELECT current_database()"))
            if database_name != "smartcampus_test":
                pytest.fail(
                    "Connexion refusée: current_database() n'est pas "
                    "smartcampus_test."
                )
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def postgres_sessions(test_postgres_engine):
    schema = f"epic23_{uuid.uuid4().hex}"
    with test_postgres_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    schema_engine = create_engine(
        test_postgres_engine.url,
        connect_args={"options": f"-csearch_path={schema}"},
        pool_pre_ping=True,
    )
    try:
        Base.metadata.create_all(schema_engine)
        factory = sessionmaker(
            bind=schema_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        yield factory
    finally:
        schema_engine.dispose()
        with test_postgres_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))


@pytest.fixture
def epic23_app(sqlite_sessions):
    previous_overrides = app.dependency_overrides.copy()
    clients = []

    def make_client(redis_store: Any, db_session_factory=None) -> TestClient:
        session_factory = db_session_factory or sqlite_sessions

        def override_db():
            with session_factory() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_redis] = lambda: redis_store
        client = TestClient(app, client=("127.0.0.1", 50000))
        clients.append(client)
        return client

    try:
        yield make_client
    finally:
        for client in clients:
            client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


def register_candidate(client: TestClient, email: str = "candidate@example.com") -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Secure-test-password-23",
            "full_name": "Candidate Test",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_candidate(client: TestClient, email: str = "candidate@example.com") -> dict:
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": "Secure-test-password-23"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def set_user_role(sqlite_sessions, user_id: int, role: str) -> None:
    with sqlite_sessions() as db:
        user = db.scalar(select(User).where(User.id == user_id))
        assert user is not None
        user.role = role
        db.commit()


def expire_guest_session(sqlite_sessions, session_id: str) -> None:
    with sqlite_sessions() as db:
        session = db.scalar(select(GuestSession).where(GuestSession.id == uuid.UUID(session_id)))
        assert session is not None
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()


def stored_messages(sqlite_sessions, conversation_id: str) -> list[Message]:
    with sqlite_sessions() as db:
        return db.scalars(
            select(Message)
            .where(Message.conversation_id == uuid.UUID(conversation_id))
            .order_by(Message.created_at.asc(), Message.id.asc())
        ).all()


def create_guest_session(client: TestClient) -> dict:
    response = client.post("/api/chat/sessions")
    assert response.status_code == 201, response.text
    body = response.json()
    assert uuid.UUID(body["guest_session_id"])
    assert body["guest_token"]
    return body


def guest_headers(session: dict) -> dict[str, str]:
    return {
        "x-guest-session": session["guest_session_id"],
        "x-guest-token": session["guest_token"],
    }


def jwt_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
