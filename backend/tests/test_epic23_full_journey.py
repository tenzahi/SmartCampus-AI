import uuid

from sqlalchemy import select

from app.db.models import Conversation, GuestSession
from app.services import chat_service
from app.services.conversation_memory import get_context
from epic23_test_support import (
    create_guest_session,
    guest_headers,
    jwt_headers,
    login_candidate,
    real_redis,
    register_candidate,
    stored_messages,
)


def test_full_guest_to_candidate_conversation_journey(
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

    # Visiteur anonyme : création, échanges, contexte Redis et messages SQL.
    guest_session = create_guest_session(client)
    first = client.post(
        "/api/chat",
        headers=guest_headers(guest_session),
        json={"message": "Je suis en bac maths."},
    )
    assert first.status_code == 200, first.text
    conversation_id = first.json()["conversation_id"]
    real_redis.track(conversation_id)
    second = client.post(
        "/api/chat",
        headers=guest_headers(guest_session),
        json={"message": "J'aime l'informatique."},
    )
    assert second.status_code == 200, second.text
    assert second.json()["conversation_id"] == conversation_id
    assert len(stored_messages(sqlite_sessions, conversation_id)) == 4
    assert [entry["content"] for entry in get_context(real_redis.client, conversation_id)] == [
        "Je suis en bac maths.",
        "Réponse 1",
        "J'aime l'informatique.",
        "Réponse 2",
    ]

    # Inscription et connexion : le rôle fourni par un client ne devient pas privilégié.
    registered = client.post(
        "/api/auth/register",
        json={
            "email": "journey@example.com",
            "password": "Secure-test-password-23",
            "full_name": "Journey Candidate",
            "role": "admin",
        },
    )
    assert registered.status_code == 201, registered.text
    token_data = login_candidate(client, "journey@example.com")
    assert token_data["user"]["role"] == "candidate"
    assert token_data["access_token"]
    candidate_id = client.get(
        "/api/auth/me",
        headers=jwt_headers(token_data["access_token"]),
    ).json()["id"]

    # Une fusion sans consentement est rejetée; l'accord explicite permet le transfert.
    claim_url = f"/api/chat/sessions/{guest_session['guest_session_id']}/claim"
    claim_body = {
        "guest_token": guest_session["guest_token"],
    }
    no_consent = client.post(
        claim_url,
        headers=jwt_headers(token_data["access_token"]),
        json={**claim_body, "consent": False},
    )
    assert no_consent.status_code == 400

    merged = client.post(
        claim_url,
        headers=jwt_headers(token_data["access_token"]),
        json={**claim_body, "consent": True},
    )
    assert merged.status_code == 200, merged.text
    assert merged.json()["status"] == "claimed"
    assert conversation_id in merged.json()["conversation_ids"]

    with sqlite_sessions() as db:
        session = db.scalar(
            select(GuestSession).where(
                GuestSession.id == uuid.UUID(guest_session["guest_session_id"])
            )
        )
        conversation = db.scalar(
            select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
        )
        assert session is not None
        assert session.status == "claimed"
        assert session.claimed_by == candidate_id
        assert session.claimed_at is not None
        assert conversation is not None
        assert conversation.candidate_id == candidate_id
    assert len(stored_messages(sqlite_sessions, conversation_id)) == 4

    double_merge = client.post(
        claim_url,
        headers=jwt_headers(token_data["access_token"]),
        json={**claim_body, "consent": True},
    )
    assert double_merge.status_code == 400

    history = client.get(
        f"/api/conversations/{conversation_id}",
        headers=jwt_headers(token_data["access_token"]),
    )
    assert history.status_code == 200, history.text
    assert [message["content"] for message in history.json()["messages"]] == [
        "Je suis en bac maths.",
        "Réponse 1",
        "J'aime l'informatique.",
        "Réponse 2",
    ]
    assert client.get(
        "/api/conversations",
        headers=jwt_headers(token_data["access_token"]),
    ).json()[0]["id"] == conversation_id
    register_candidate(client, "other-candidate@example.com")
    other_token = login_candidate(client, "other-candidate@example.com")
    forbidden_history = client.get(
        f"/api/conversations/{conversation_id}",
        headers=jwt_headers(other_token["access_token"]),
    )
    assert forbidden_history.status_code == 404

    # Le candidat continue la même session; les tours précédents restent dans le contexte.
    continued = client.post(
        "/api/chat",
        headers={
            **guest_headers(guest_session),
            **jwt_headers(token_data["access_token"]),
        },
        json={"message": "Quelle formation me conseilles-tu ?"},
    )
    assert continued.status_code == 200, continued.text
    assert continued.json()["conversation_id"] == conversation_id
    assert [message["content"] for message in observed_contexts[-1]] == [
        "Je suis en bac maths.",
        "Réponse 1",
        "J'aime l'informatique.",
        "Réponse 2",
        "Quelle formation me conseilles-tu ?",
    ]
    assert len(stored_messages(sqlite_sessions, conversation_id)) == 6

    own_history = client.get(
        f"/api/conversations/{conversation_id}",
        headers=jwt_headers(token_data["access_token"]),
    )
    assert own_history.status_code == 200
    assert own_history.json()["messages"][-2]["content"] == "Quelle formation me conseilles-tu ?"
    assert own_history.json()["messages"][-1]["content"] == "Réponse 3"
