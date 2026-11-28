import json
import uuid

from sqlalchemy import select

from app.db.models import ConversationProfile, GuestSession
from app.services import chat_service, conversation_memory
from epic23_test_support import (
    create_guest_session,
    guest_headers,
    real_redis,
    stored_messages,
)


def test_guest_session_messages_and_redis_memory_are_persisted(
    epic23_app,
    real_redis,
    sqlite_sessions,
    monkeypatch,
):
    observed_contexts = []

    def fake_answer(context, profile):
        observed_contexts.append([dict(message) for message in context])
        return f"Réponse {len(observed_contexts)}"

    monkeypatch.setattr(chat_service, "generate_answer", fake_answer)
    client = epic23_app(real_redis.client)

    session = create_guest_session(client)
    with sqlite_sessions() as db:
        stored_session = db.scalar(
            select(GuestSession).where(
                GuestSession.id == uuid.UUID(session["guest_session_id"])
            )
        )
        assert stored_session is not None
        assert stored_session.guest_token_hash != session["guest_token"]
        assert stored_session.status == "active"

    verified = client.get(
        "/api/chat/sessions/me",
        headers=guest_headers(session),
    )
    assert verified.status_code == 200
    assert verified.json()["guest_session_id"] == session["guest_session_id"]

    first = client.post(
        "/api/chat",
        headers=guest_headers(session),
        json={"message": "Je suis en bac maths."},
    )
    assert first.status_code == 200, first.text
    real_redis.track(first.json()["conversation_id"])
    second = client.post(
        "/api/chat",
        headers=guest_headers(session),
        json={"message": "J'aime l'informatique."},
    )
    assert second.status_code == 200, second.text

    conversation_id = first.json()["conversation_id"]
    assert second.json()["conversation_id"] == conversation_id
    persisted = stored_messages(sqlite_sessions, conversation_id)
    assert [(message.role, message.content) for message in persisted] == [
        ("user", "Je suis en bac maths."),
        ("assistant", "Réponse 1"),
        ("user", "J'aime l'informatique."),
        ("assistant", "Réponse 2"),
    ]

    redis_history = conversation_memory.get_context(
        real_redis.client,
        conversation_id,
    )
    assert [message["content"] for message in redis_history] == [
        "Je suis en bac maths.",
        "Réponse 1",
        "J'aime l'informatique.",
        "Réponse 2",
    ]
    assert observed_contexts[0] == [
        {"role": "user", "content": "Je suis en bac maths."}
    ]
    assert [message["content"] for message in observed_contexts[1]] == [
        "Je suis en bac maths.",
        "Réponse 1",
        "J'aime l'informatique.",
    ]
    profile_key = f"conv:{conversation_id}:profile"
    assert json.loads(real_redis.client.get(profile_key))["status"] == "en_cours_d_orientation"
    assert real_redis.client.ttl(f"conv:{conversation_id}:messages") > 0
    assert real_redis.client.ttl(profile_key) > 0


def test_missing_redis_memory_is_restored_from_postgres(
    epic23_app,
    real_redis,
    sqlite_sessions,
    monkeypatch,
):
    observed = []

    def fake_answer(context, profile):
        observed.append(([dict(message) for message in context], dict(profile)))
        return "Réponse persistée"

    monkeypatch.setattr(chat_service, "generate_answer", fake_answer)
    client = epic23_app(real_redis.client)
    session = create_guest_session(client)

    first = client.post(
        "/api/chat",
        headers=guest_headers(session),
        json={"message": "Je suis en bac maths, ma moyenne est 14."},
    )
    assert first.status_code == 200, first.text
    conversation_id = first.json()["conversation_id"]
    real_redis.track(conversation_id)

    with sqlite_sessions() as db:
        stored_profile = db.get(
            ConversationProfile,
            uuid.UUID(conversation_id),
        )
        assert stored_profile is not None
        expected_profile = dict(stored_profile.profile_json)

    real_redis.client.delete(
        f"conv:{conversation_id}:messages",
        f"conv:{conversation_id}:profile",
    )

    second = client.post(
        "/api/chat",
        headers=guest_headers(session),
        json={"message": "Je voudrais une réponse."},
    )

    assert second.status_code == 200, second.text
    assert observed[1][0] == [
        {"role": "user", "content": "Je suis en bac maths, ma moyenne est 14."},
        {"role": "assistant", "content": "Réponse persistée"},
        {"role": "user", "content": "Je voudrais une réponse."},
    ]
    assert observed[1][1] == expected_profile
