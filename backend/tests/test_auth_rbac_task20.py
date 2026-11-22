import os

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.dependencies import catalogue_writer
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db
from app.main import app
from app.services.specialite_service import SpecialiteService


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _database_isolee():
    # Seule la table ``users`` est nécessaire ici : les tables chat utilisent
    # des types PostgreSQL (JSONB, INET) que SQLite ne peut pas créer.
    tables = [User.__table__]
    Base.metadata.drop_all(bind=test_engine, tables=tables)
    Base.metadata.create_all(bind=test_engine, tables=tables)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # On teste le vrai garde RBAC, pas l'override des tests métier Task20.
    app.dependency_overrides.pop(catalogue_writer, None)
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(catalogue_writer, None)


def _register(
    email: str = "candidat@example.com",
    password: str = "motdepasse123",
    full_name: str = "Candidat Test",
):
    return client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )


def _login(email: str = "candidat@example.com", password: str = "motdepasse123"):
    return client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )


def _token(email: str = "candidat@example.com", password: str = "motdepasse123"):
    response = _login(email, password)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _set_role(email: str, role: str) -> None:
    with TestingSessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role
        db.commit()


def _specialite_read() -> dict:
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


def _specialite_payload() -> dict:
    return {
        "programme_id": 1,
        "nom": "Génie logiciel",
        "code": "GL",
        "description": None,
        "actif": True,
    }


def test_inscription_connexion_et_profil():
    response = _register()
    assert response.status_code == 201
    assert response.json()["user_id"] == 1

    duplicate = _register()
    assert duplicate.status_code == 400

    login = _login()
    assert login.status_code == 200
    body = login.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "candidate"
    assert body["access_token"]

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "candidat@example.com"
    assert me.json()["role"] == "candidate"


def test_connexion_refuse_un_mauvais_mot_de_passe():
    _register()

    response = _login(password="mauvais")

    assert response.status_code == 401


def test_profil_refuse_absence_ou_invalidite_du_token():
    assert client.get("/api/auth/me").status_code == 401
    assert (
        client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer token-invalide"},
        ).status_code
        == 401
    )


def test_ecriture_task20_exige_un_token():
    response = client.post("/api/specialites", json=_specialite_payload())

    assert response.status_code == 401


def test_ecriture_formation_exige_un_token():
    response = client.post(
        "/api/formations",
        json={
            "nom": "Formation test",
            "etablissement": "IIT",
            "niveau": "Licence",
            "description": None,
        },
    )

    assert response.status_code == 401


@pytest.mark.parametrize("method", ["put", "delete"])
def test_mise_a_jour_et_suppression_exigent_un_token(method):
    response = client.request(method, "/api/specialites/1", json={})

    assert response.status_code == 401


def test_ecriture_task20_refuse_un_candidat():
    _register()
    token = _token()

    response = client.post(
        "/api/specialites",
        json=_specialite_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize("role", ["admin", "resp_iit", "resp_isb"])
def test_ecriture_task20_autorise_les_roles_metier(monkeypatch, role):
    monkeypatch.setattr(
        SpecialiteService,
        "create_specialite",
        lambda payload: _specialite_read(),
    )
    _register()
    _set_role("candidat@example.com", role)
    token = _token()

    response = client.post(
        "/api/specialites",
        json=_specialite_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["code"] == "GL"


def test_lecture_task20_reste_publique(monkeypatch):
    monkeypatch.setattr(
        SpecialiteService,
        "list_specialites",
        lambda **kwargs: [_specialite_read()],
    )

    response = client.get("/api/specialites")

    assert response.status_code == 200
    assert response.json()[0]["code"] == "GL"
