from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import time
import uuid

from sqlalchemy import func, select

from app.core.config import settings
from app.db.models import Conversation, GuestSession
from app.services import chat_service
from epic23_test_support import (
    create_guest_session,
    guest_headers,
    jwt_headers,
    login_candidate,
    real_redis,
    register_candidate,
    stored_messages,
)


def test_chat_messages_are_persisted_in_isolated_postgres(
    epic23_app,
    postgres_sessions,
    real_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda context, profile: "Réponse test PostgreSQL",
    )
    client = epic23_app(real_redis.client, postgres_sessions)
    guest_session = create_guest_session(client)

    response = client.post(
        "/api/chat",
        headers=guest_headers(guest_session),
        json={"message": "Message conservé dans PostgreSQL"},
    )
    assert response.status_code == 200, response.text
    conversation_id = response.json()["conversation_id"]
    real_redis.track(conversation_id)

    messages = stored_messages(postgres_sessions, conversation_id)
    assert [(message.role, message.content) for message in messages] == [
        ("user", "Message conservé dans PostgreSQL"),
        ("assistant", "Réponse test PostgreSQL"),
    ]


def test_concurrent_guest_session_creation_respects_ip_limit(
    epic23_app,
    postgres_sessions,
    fake_redis,
    monkeypatch,
):
    limit = 2
    request_count = 8
    monkeypatch.setattr(settings, "guest_session_max_per_ip", limit)
    clients = [
        epic23_app(fake_redis, postgres_sessions)
        for _ in range(request_count)
    ]
    start_barrier = Barrier(request_count)

    def create_session(client):
        start_barrier.wait(timeout=15)
        return client.post("/api/chat/sessions")

    with ThreadPoolExecutor(max_workers=request_count) as executor:
        futures = [
            executor.submit(create_session, client)
            for client in clients
        ]
        responses = [future.result(timeout=30) for future in futures]

    assert sorted(response.status_code for response in responses) == [
        201,
        201,
        *([429] * (request_count - limit)),
    ]
    with postgres_sessions() as db:
        stored_count = db.scalar(
            select(func.count())
            .select_from(GuestSession)
            .where(GuestSession.ip_address == "127.0.0.1")
        )
    assert stored_count == limit


def test_concurrent_first_messages_share_one_conversation(
    epic23_app,
    postgres_sessions,
    real_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda context, profile: "Réponse concurrente",
    )
    client_a = epic23_app(real_redis.client, postgres_sessions)
    client_b = epic23_app(real_redis.client, postgres_sessions)
    guest_session = create_guest_session(client_a)
    validation_barrier = Barrier(2)
    original_validate = chat_service.validate_guest_session

    def synchronized_validate(*args, **kwargs):
        result = original_validate(*args, **kwargs)
        if result is not None:
            validation_barrier.wait(timeout=15)
        return result

    monkeypatch.setattr(chat_service, "validate_guest_session", synchronized_validate)

    def send(client, message):
        return client.post(
            "/api/chat",
            headers=guest_headers(guest_session),
            json={"message": message},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(send, client_a, "Concurrent message A"),
            executor.submit(send, client_b, "Concurrent message B"),
        ]
        responses = [future.result(timeout=30) for future in futures]

    assert [response.status_code for response in responses] == [200, 200]
    conversation_ids = [response.json()["conversation_id"] for response in responses]
    for conversation_id in set(conversation_ids):
        real_redis.track(conversation_id)
    assert conversation_ids[0] == conversation_ids[1]

    with postgres_sessions() as db:
        conversations = db.scalars(
            select(Conversation).where(
                Conversation.guest_session_id
                == uuid.UUID(guest_session["guest_session_id"])
            )
        ).all()
    assert len(conversations) == 1
    assert len(stored_messages(postgres_sessions, conversation_ids[0])) == 4


def test_candidate_conversation_order_tracks_latest_message_activity(
    epic23_app,
    postgres_sessions,
    real_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda context, profile: "Réponse tri",
    )
    client = epic23_app(real_redis.client, postgres_sessions)
    register_candidate(client, "activity-owner@example.com")
    candidate_token = login_candidate(
        client,
        "activity-owner@example.com",
    )["access_token"]

    first_session = create_guest_session(client)
    first_response = client.post(
        "/api/chat",
        headers=guest_headers(first_session),
        json={"message": "Première session"},
    )
    assert first_response.status_code == 200, first_response.text
    first_conversation_id = first_response.json()["conversation_id"]
    real_redis.track(first_conversation_id)

    time.sleep(0.01)
    second_session = create_guest_session(client)
    second_response = client.post(
        "/api/chat",
        headers=guest_headers(second_session),
        json={"message": "Deuxième session"},
    )
    assert second_response.status_code == 200, second_response.text
    second_conversation_id = second_response.json()["conversation_id"]
    real_redis.track(second_conversation_id)

    for session in (first_session, second_session):
        claimed = client.post(
            f"/api/chat/sessions/{session['guest_session_id']}/claim",
            headers=jwt_headers(candidate_token),
            json={
                "guest_token": session["guest_token"],
                "consent": True,
            },
        )
        assert claimed.status_code == 200, claimed.text

    time.sleep(0.01)
    latest = client.post(
        "/api/chat",
        headers={
            **guest_headers(first_session),
            **jwt_headers(candidate_token),
        },
        json={"message": "Activité la plus récente"},
    )
    assert latest.status_code == 200, latest.text

    listing = client.get(
        "/api/conversations",
        headers=jwt_headers(candidate_token),
    )
    assert listing.status_code == 200
    assert listing.json()[0]["id"] == first_conversation_id
    assert listing.json()[1]["id"] == second_conversation_id
