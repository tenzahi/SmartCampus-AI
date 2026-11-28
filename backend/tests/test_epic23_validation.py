import pytest

from app.core.security import decode_access_token
from app.core.config import settings
from app.services import chat_service
from app.services.specialite_service import SpecialiteService
from epic23_test_support import (
    create_guest_session,
    fake_redis,
    guest_headers,
    login_candidate,
    real_redis,
    register_candidate,
    set_user_role,
    jwt_headers,
    stored_messages,
)


def _specialite_payload():
    return {
        "programme_id": 1,
        "nom": "Génie logiciel",
        "code": "GL",
        "description": None,
        "actif": True,
    }


def _specialite_read():
    return {
        "id": 1,
        "programme_id": 1,
        "nom": "Génie logiciel",
        "code": "GL",
        "description": None,
        "actif": True,
        "created_at": None,
        "updated_at": None,
    }


def test_anonymous_chat_works_without_jwt(epic23_app, fake_redis, monkeypatch):
    monkeypatch.setattr(chat_service, "generate_answer", lambda context, profile: "Bonjour")
    client = epic23_app(fake_redis)
    session = create_guest_session(client)

    response = client.post(
        "/api/chat",
        headers=guest_headers(session),
        json={"message": "Bonjour"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["answer"] == "Bonjour"


@pytest.mark.parametrize(
    "headers",
    [
        {"x-guest-session": "not-a-uuid", "x-guest-token": "bad-token"},
        {"x-guest-session": "00000000-0000-0000-0000-000000000000", "x-guest-token": "bad-token"},
    ],
)
def test_chat_refuse_une_session_invalide(epic23_app, fake_redis, headers):
    client = epic23_app(fake_redis)

    response = client.post("/api/chat", headers=headers, json={"message": "Bonjour"})

    assert response.status_code == 401


def test_chat_refuse_une_session_expiree(epic23_app, fake_redis, sqlite_sessions):
    from epic23_test_support import expire_guest_session

    client = epic23_app(fake_redis)
    session = create_guest_session(client)
    expire_guest_session(sqlite_sessions, session["guest_session_id"])

    response = client.post(
        "/api/chat",
        headers=guest_headers(session),
        json={"message": "Bonjour"},
    )

    assert response.status_code == 401


def test_chat_refuse_un_role_non_candidat(epic23_app, fake_redis, sqlite_sessions):
    client = epic23_app(fake_redis)
    registered = register_candidate(client, "responsable@example.com")
    set_user_role(sqlite_sessions, registered["user_id"], "responsable_nau")
    token_data = login_candidate(client, "responsable@example.com")
    session = create_guest_session(client)

    response = client.post(
        "/api/chat",
        headers={
            **guest_headers(session),
            **jwt_headers(token_data["access_token"]),
        },
        json={"message": "Bonjour"},
    )

    assert response.status_code == 403


def test_chat_rejects_empty_and_overlong_messages(epic23_app, fake_redis):
    client = epic23_app(fake_redis)
    session = create_guest_session(client)

    empty = client.post(
        "/api/chat",
        headers=guest_headers(session),
        json={"message": "   "},
    )
    overlong = client.post(
        "/api/chat",
        headers=guest_headers(session),
        json={"message": "x" * (settings.chat_message_max_length + 1)},
    )

    assert empty.status_code == 422
    assert overlong.status_code == 422


def test_chat_enforces_configured_user_message_quota(
    epic23_app,
    fake_redis,
    sqlite_sessions,
    monkeypatch,
):
    monkeypatch.setattr(chat_service, "generate_answer", lambda context, profile: "Réponse")
    monkeypatch.setattr(settings, "guest_session_max_messages", 2)
    client = epic23_app(fake_redis)
    session = create_guest_session(client)

    for message in ("Premier message", "Deuxième message"):
        response = client.post(
            "/api/chat",
            headers=guest_headers(session),
            json={"message": message},
        )
        assert response.status_code == 200, response.text

    conversation_id = response.json()["conversation_id"]
    before = stored_messages(sqlite_sessions, conversation_id)
    limited = client.post(
        "/api/chat",
        headers=guest_headers(session),
        json={"message": "Troisième message"},
    )

    assert limited.status_code == 429
    assert "limite" in limited.json()["detail"].lower()
    assert [
        (message.role, message.content) for message in
        stored_messages(sqlite_sessions, conversation_id)
    ] == [
        (message.role, message.content) for message in before
    ]


def test_payload_chat_invalide_et_endpoints_prives(epic23_app, fake_redis):
    client = epic23_app(fake_redis)

    assert client.post("/api/chat", json={}).status_code == 422
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/conversations").status_code == 401
    assert client.get("/api/admin/users").status_code == 401
    assert (
        client.post(
            "/api/chat/sessions/00000000-0000-0000-0000-000000000000/claim",
            json={},
        ).status_code
        == 401
    )


def test_merge_refuse_sans_consentement(epic23_app, fake_redis):
    client = epic23_app(fake_redis)
    register_candidate(client)
    token_data = login_candidate(client)
    session = create_guest_session(client)

    response = client.post(
        f"/api/chat/sessions/{session['guest_session_id']}/claim",
        headers=jwt_headers(token_data["access_token"]),
        json={
            "guest_token": session["guest_token"],
            "consent": False,
        },
    )

    assert response.status_code == 400
    assert "consentement" in response.json()["detail"].lower()


def test_merge_refuse_un_role_non_candidat(epic23_app, fake_redis, sqlite_sessions):
    client = epic23_app(fake_redis)
    registered = register_candidate(client, "responsable-merge@example.com")
    set_user_role(sqlite_sessions, registered["user_id"], "responsable_nau")
    token_data = login_candidate(client, "responsable-merge@example.com")
    session = create_guest_session(client)

    response = client.post(
        f"/api/chat/sessions/{session['guest_session_id']}/claim",
        headers=jwt_headers(token_data["access_token"]),
        json={
            "guest_token": session["guest_token"],
            "consent": True,
        },
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [("candidate", 403), ("responsable_nau", 201), ("admin", 201)],
)
def test_roles_officiels_et_droits_catalogue(
    epic23_app,
    fake_redis,
    sqlite_sessions,
    monkeypatch,
    role,
    expected_status,
):
    monkeypatch.setattr(
        SpecialiteService,
        "create_specialite",
        lambda payload: _specialite_read(),
    )
    client = epic23_app(fake_redis)
    registered = register_candidate(client, f"{role}@example.com")
    set_user_role(sqlite_sessions, registered["user_id"], role)
    token_data = login_candidate(client, f"{role}@example.com")

    response = client.post(
        "/api/specialites",
        headers=jwt_headers(token_data["access_token"]),
        json=_specialite_payload(),
    )

    assert response.status_code == expected_status, response.text
    if expected_status == 201:
        assert response.json()["code"] == "GL"


@pytest.mark.parametrize("role", ["candidate", "responsable_nau"])
def test_only_admin_can_manage_users(epic23_app, fake_redis, sqlite_sessions, role):
    client = epic23_app(fake_redis)
    registered = register_candidate(client, f"{role}@example.com")
    set_user_role(sqlite_sessions, registered["user_id"], role)
    token_data = login_candidate(client, f"{role}@example.com")

    response = client.get(
        "/api/admin/users",
        headers=jwt_headers(token_data["access_token"]),
    )

    assert response.status_code == 403


def test_administrateur_gere_les_roles_et_le_candidat_ne_peut_pas_s_autopromouvoir(
    epic23_app,
    fake_redis,
    sqlite_sessions,
):
    client = epic23_app(fake_redis)
    candidate = register_candidate(client)
    candidate_token = login_candidate(client)

    denied = client.patch(
        f"/api/admin/users/{candidate['user_id']}/role",
        headers=jwt_headers(candidate_token["access_token"]),
        json={"role": "admin"},
    )
    assert denied.status_code == 403
    assert client.patch(
        "/api/users/me/role",
        headers=jwt_headers(candidate_token["access_token"]),
        json={"role": "admin"},
    ).status_code == 404

    set_user_role(sqlite_sessions, candidate["user_id"], "admin")
    admin_token = login_candidate(client)
    listing = client.get(
        "/api/admin/users",
        headers=jwt_headers(admin_token["access_token"]),
    )
    assert listing.status_code == 200

    updated = client.patch(
        f"/api/admin/users/{candidate['user_id']}/role",
        headers=jwt_headers(admin_token["access_token"]),
        json={"role": "responsable_nau"},
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "responsable_nau"


def test_inscription_ignore_un_role_privilegie(epic23_app, fake_redis, sqlite_sessions):
    client = epic23_app(fake_redis)
    response = client.post(
        "/api/auth/register",
        json={
            "email": "role-injection@example.com",
            "password": "Secure-test-password-23",
            "full_name": "Candidate Test",
            "role": "admin",
        },
    )

    assert response.status_code == 201
    profile = client.post(
        "/api/auth/login",
        data={
            "username": "role-injection@example.com",
            "password": "Secure-test-password-23",
        },
    )
    assert profile.status_code == 200
    assert profile.json()["user"]["role"] == "candidate"


def test_logout_invalide_le_jwt_dans_redis_reel(epic23_app, real_redis):
    client = epic23_app(real_redis.client)
    register_candidate(client)
    token = login_candidate(client)["access_token"]
    claims = decode_access_token(token)
    assert claims is not None
    jti = claims["jti"]
    real_redis.track_key(f"revoked_jwt:{jti}")
    headers = jwt_headers(token)

    assert client.get("/api/auth/me", headers=headers).status_code == 200

    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert real_redis.client.get(f"revoked_jwt:{jti}") == "1"
    assert real_redis.client.ttl(f"revoked_jwt:{jti}") > 0
    assert client.get("/api/auth/me", headers=headers).status_code == 401
