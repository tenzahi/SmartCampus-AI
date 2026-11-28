import uuid

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select

from app.core.security import decode_access_token
from app.db.models import Conversation, ConversationProfile, GuestSession
from app.services import chat_service
from app.services.guest_session_service import (
    cleanup_expired_guest_sessions,
    hash_token,
)
from epic23_test_support import (
    create_guest_session,
    expire_guest_session,
    guest_headers,
    jwt_headers,
    login_candidate,
    real_redis,
    register_candidate,
    set_user_role,
    stored_messages,
)


def _send_chat(client, session, message, access_token=None):
    headers = guest_headers(session)
    if access_token is not None:
        headers.update(jwt_headers(access_token))
    return client.post(
        "/api/chat",
        headers=headers,
        json={"message": message},
    )


def _claim_session(client, session, access_token, consent=True):
    return client.post(
        f"/api/chat/sessions/{session['guest_session_id']}/claim",
        headers=jwt_headers(access_token),
        json={"guest_token": session["guest_token"], "consent": consent},
    )


def _session_state(postgres_sessions, session_id):
    with postgres_sessions() as db:
        session = db.get(GuestSession, uuid.UUID(session_id))
        assert session is not None
        return session.status, session.claimed_by, session.guest_token_hash


def _conversation_count(postgres_sessions, session_id):
    with postgres_sessions() as db:
        return len(
            db.scalars(
                select(Conversation).where(
                    Conversation.guest_session_id == uuid.UUID(session_id)
                )
            ).all()
        )


def test_guest_session_creation_status_and_token_validation(
    epic23_app,
    postgres_sessions,
    real_redis,
):
    client = epic23_app(real_redis.client, postgres_sessions)
    session = create_guest_session(client)

    status, claimed_by, token_hash = _session_state(
        postgres_sessions,
        session["guest_session_id"],
    )
    assert status == "active"
    assert claimed_by is None
    assert token_hash == hash_token(session["guest_token"])

    verified = client.get(
        "/api/chat/sessions/me",
        headers=guest_headers(session),
    )
    assert verified.status_code == 200
    assert verified.json()["guest_session_id"] == session["guest_session_id"]
    assert verified.json()["status"] == "active"


def test_claimed_session_rejects_anonymous_token_without_disclosing_history(
    epic23_app,
    postgres_sessions,
    real_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda context, profile: "private assistant reply",
    )
    client = epic23_app(real_redis.client, postgres_sessions)
    session = create_guest_session(client)
    first_message = "private conversation marker"
    first = _send_chat(client, session, first_message)
    assert first.status_code == 200, first.text
    conversation_id = first.json()["conversation_id"]
    real_redis.track(conversation_id)
    before = [
        (message.role, message.content)
        for message in stored_messages(postgres_sessions, conversation_id)
    ]

    register_candidate(client, "claim-owner@example.com")
    owner_token = login_candidate(client, "claim-owner@example.com")["access_token"]
    claimed = _claim_session(client, session, owner_token)
    assert claimed.status_code == 200, claimed.text

    anonymous_access = _send_chat(client, session, "unauthorized follow-up")
    assert anonymous_access.status_code == 401
    assert conversation_id not in anonymous_access.text
    assert first_message not in anonymous_access.text
    assert "private assistant reply" not in anonymous_access.text
    assert [
        (message.role, message.content)
        for message in stored_messages(postgres_sessions, conversation_id)
    ] == before


def test_claimed_session_remains_available_to_its_candidate_owner(
    epic23_app,
    postgres_sessions,
    real_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda context, profile: "stored assistant reply",
    )
    client = epic23_app(real_redis.client, postgres_sessions)
    register_candidate(client, "owner@example.com")
    owner_token = login_candidate(client, "owner@example.com")["access_token"]
    session = create_guest_session(client)

    first = _send_chat(client, session, "history before claim")
    assert first.status_code == 200, first.text
    conversation_id = first.json()["conversation_id"]
    real_redis.track(conversation_id)
    claimed = _claim_session(client, session, owner_token)
    assert claimed.status_code == 200, claimed.text

    continued = _send_chat(
        client,
        session,
        "owner follow-up",
        access_token=owner_token,
    )
    assert continued.status_code == 200, continued.text
    assert continued.json()["conversation_id"] == conversation_id

    history = client.get(
        f"/api/conversations/{conversation_id}",
        headers=jwt_headers(owner_token),
    )
    assert history.status_code == 200, history.text
    assert [
        message["content"] for message in history.json()["messages"]
    ] == [
        "history before claim",
        "stored assistant reply",
        "owner follow-up",
        "stored assistant reply",
    ]
    assert [
        (message.role, message.content)
        for message in stored_messages(postgres_sessions, conversation_id)
    ] == [
        ("user", "history before claim"),
        ("assistant", "stored assistant reply"),
        ("user", "owner follow-up"),
        ("assistant", "stored assistant reply"),
    ]


def test_claimed_session_rejects_a_different_candidate(
    epic23_app,
    postgres_sessions,
    real_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda context, profile: "owner-only history",
    )
    client = epic23_app(real_redis.client, postgres_sessions)
    register_candidate(client, "owner@example.com")
    owner_token = login_candidate(client, "owner@example.com")["access_token"]
    register_candidate(client, "other@example.com")
    other_token = login_candidate(client, "other@example.com")["access_token"]
    session = create_guest_session(client)

    first = _send_chat(client, session, "owner-only marker")
    assert first.status_code == 200, first.text
    conversation_id = first.json()["conversation_id"]
    real_redis.track(conversation_id)
    claimed = _claim_session(client, session, owner_token)
    assert claimed.status_code == 200, claimed.text
    before = [
        (message.role, message.content)
        for message in stored_messages(postgres_sessions, conversation_id)
    ]

    denied = _send_chat(
        client,
        session,
        "unauthorized candidate message",
        access_token=other_token,
    )
    assert denied.status_code == 401
    assert conversation_id not in denied.text
    assert "owner-only marker" not in denied.text
    assert [
        (message.role, message.content)
        for message in stored_messages(postgres_sessions, conversation_id)
    ] == before

    other_history = client.get(
        f"/api/conversations/{conversation_id}",
        headers=jwt_headers(other_token),
    )
    assert other_history.status_code == 404


def test_invalid_guest_token_does_not_create_or_modify_conversation(
    epic23_app,
    postgres_sessions,
    real_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda context, profile: "valid assistant reply",
    )
    client = epic23_app(real_redis.client, postgres_sessions)
    session = create_guest_session(client)
    first = _send_chat(client, session, "valid initial message")
    assert first.status_code == 200, first.text
    conversation_id = first.json()["conversation_id"]
    real_redis.track(conversation_id)
    before = [
        (message.role, message.content)
        for message in stored_messages(postgres_sessions, conversation_id)
    ]

    invalid_session = {**session, "guest_token": "invalid-test-token"}
    denied = _send_chat(client, invalid_session, "must not be stored")

    assert denied.status_code == 401
    assert _conversation_count(postgres_sessions, session["guest_session_id"]) == 1
    assert [
        (message.role, message.content)
        for message in stored_messages(postgres_sessions, conversation_id)
    ] == before


def test_claim_without_consent_leaves_session_active_and_unclaimed(
    epic23_app,
    postgres_sessions,
    real_redis,
):
    client = epic23_app(real_redis.client, postgres_sessions)
    register_candidate(client, "consent@example.com")
    candidate_token = login_candidate(client, "consent@example.com")["access_token"]
    session = create_guest_session(client)

    refused = _claim_session(client, session, candidate_token, consent=False)

    assert refused.status_code == 400
    status, claimed_by, _ = _session_state(
        postgres_sessions,
        session["guest_session_id"],
    )
    assert status == "active"
    assert claimed_by is None


def test_second_claim_is_refused_and_does_not_change_other_sessions(
    epic23_app,
    postgres_sessions,
    real_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda context, profile: "claim test reply",
    )
    client = epic23_app(real_redis.client, postgres_sessions)
    owner = register_candidate(client, "first-owner@example.com")
    owner_token = login_candidate(client, "first-owner@example.com")["access_token"]
    register_candidate(client, "second-owner@example.com")
    other_token = login_candidate(client, "second-owner@example.com")["access_token"]
    session = create_guest_session(client)
    unrelated_session = create_guest_session(client)

    first_message = _send_chat(client, session, "message to claim")
    assert first_message.status_code == 200, first_message.text
    conversation_id = first_message.json()["conversation_id"]
    real_redis.track(conversation_id)

    first_claim = _claim_session(client, session, owner_token)
    assert first_claim.status_code == 200, first_claim.text
    second_claim = _claim_session(client, session, other_token)
    assert second_claim.status_code == 400

    status, claimed_by, _ = _session_state(
        postgres_sessions,
        session["guest_session_id"],
    )
    assert status == "claimed"
    assert claimed_by == owner["user_id"]
    unrelated_status, unrelated_owner, _ = _session_state(
        postgres_sessions,
        unrelated_session["guest_session_id"],
    )
    assert unrelated_status == "active"
    assert unrelated_owner is None

    with postgres_sessions() as db:
        conversation = db.get(Conversation, uuid.UUID(conversation_id))
        assert conversation is not None
        assert conversation.candidate_id == owner["user_id"]


def test_revoked_candidate_token_cannot_continue_claimed_chat(
    epic23_app,
    postgres_sessions,
    real_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda context, profile: "response before revocation",
    )
    client = epic23_app(real_redis.client, postgres_sessions)
    register_candidate(client, "revoked-owner@example.com")
    owner_token = login_candidate(client, "revoked-owner@example.com")["access_token"]
    claims = decode_access_token(owner_token)
    assert claims is not None
    real_redis.track_key(f"revoked_jwt:{claims['jti']}")
    session = create_guest_session(client)

    first = _send_chat(client, session, "message before revocation")
    assert first.status_code == 200, first.text
    conversation_id = first.json()["conversation_id"]
    real_redis.track(conversation_id)
    claimed = _claim_session(client, session, owner_token)
    assert claimed.status_code == 200, claimed.text
    before = [
        (message.role, message.content)
        for message in stored_messages(postgres_sessions, conversation_id)
    ]

    logout = client.post(
        "/api/auth/logout",
        headers=jwt_headers(owner_token),
    )
    assert logout.status_code == 200

    denied = _send_chat(
        client,
        session,
        "must not pass revoked token",
        access_token=owner_token,
    )
    assert denied.status_code == 401
    assert conversation_id not in denied.text
    assert [
        (message.role, message.content)
        for message in stored_messages(postgres_sessions, conversation_id)
    ] == before


@pytest.mark.parametrize("role", ["responsable_nau", "admin"])
def test_only_candidates_can_claim_guest_sessions(
    epic23_app,
    postgres_sessions,
    real_redis,
    monkeypatch,
    role,
):
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda context, profile: "claim role test reply",
    )
    client = epic23_app(real_redis.client, postgres_sessions)
    user = register_candidate(client, f"claim-{role}@example.com")
    set_user_role(postgres_sessions, user["user_id"], role)
    access_token = login_candidate(client, f"claim-{role}@example.com")["access_token"]
    session = create_guest_session(client)

    first = _send_chat(client, session, "session remains unclaimed")
    assert first.status_code == 200, first.text
    conversation_id = first.json()["conversation_id"]
    real_redis.track(conversation_id)

    denied = _claim_session(client, session, access_token)

    assert denied.status_code == 403
    status, claimed_by, _ = _session_state(
        postgres_sessions,
        session["guest_session_id"],
    )
    assert status == "active"
    assert claimed_by is None


def test_redis_outage_fails_closed_for_authenticated_requests(
    epic23_app,
    postgres_sessions,
):
    class UnavailableRedis:
        def get(self, key):
            raise RedisConnectionError("simulated test outage")

    client = epic23_app(UnavailableRedis(), postgres_sessions)
    register_candidate(client, "redis-outage@example.com")
    access_token = login_candidate(client, "redis-outage@example.com")["access_token"]

    response = client.get(
        "/api/auth/me",
        headers=jwt_headers(access_token),
    )

    assert response.status_code == 503
    assert "simulated test outage" not in response.text

    chat_response = client.post(
        "/api/chat",
        headers=jwt_headers(access_token),
        json={"message": "must fail closed"},
    )
    assert chat_response.status_code == 503
    assert "simulated test outage" not in chat_response.text


def test_cleanup_removes_expired_guest_data_and_preserves_claimed_history(
    epic23_app,
    sqlite_sessions,
    real_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda context, profile: "Réponse conservée",
    )
    client = epic23_app(real_redis.client)
    register_candidate(client, "retention-owner@example.com")
    owner_token = login_candidate(
        client,
        "retention-owner@example.com",
    )["access_token"]

    anonymous_session = create_guest_session(client)
    anonymous_response = _send_chat(
        client,
        anonymous_session,
        "Conversation visiteur expirée",
    )
    assert anonymous_response.status_code == 200
    anonymous_conversation_id = anonymous_response.json()["conversation_id"]
    real_redis.track(anonymous_conversation_id)

    claimed_session = create_guest_session(client)
    claimed_response = _send_chat(
        client,
        claimed_session,
        "Conversation rattachée conservée",
    )
    assert claimed_response.status_code == 200
    claimed_conversation_id = claimed_response.json()["conversation_id"]
    real_redis.track(claimed_conversation_id)
    claim = _claim_session(client, claimed_session, owner_token)
    assert claim.status_code == 200, claim.text

    expire_guest_session(sqlite_sessions, anonymous_session["guest_session_id"])
    expire_guest_session(sqlite_sessions, claimed_session["guest_session_id"])

    with sqlite_sessions() as db:
        deleted_count = cleanup_expired_guest_sessions(db, batch_size=10)

    assert deleted_count == 2
    assert stored_messages(sqlite_sessions, anonymous_conversation_id) == []
    with sqlite_sessions() as db:
        assert db.get(Conversation, uuid.UUID(anonymous_conversation_id)) is None
        preserved = db.get(Conversation, uuid.UUID(claimed_conversation_id))
        assert preserved is not None
        assert preserved.candidate_id is not None
        assert preserved.guest_session_id is None
        assert db.get(
            ConversationProfile,
            uuid.UUID(claimed_conversation_id),
        ) is not None
    assert [
        message.content
        for message in stored_messages(sqlite_sessions, claimed_conversation_id)
    ] == ["Conversation rattachée conservée", "Réponse conservée"]
