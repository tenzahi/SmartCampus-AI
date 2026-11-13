"""Vérifications statiques de la configuration de sécurité.

Aucun test ici n'ouvre de connexion PostgreSQL : les contrôles de démarrage
sont exécutés dans des sous-processus Python avec ``DATABASE_URL=sqlite://``
(le moteur SQLAlchemy est créé mais jamais connecté).
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.security import (
    MIN_SECRET_KEY_LENGTH,
    validate_secret_key,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATION_FILE = (
    BACKEND_DIR
    / "alembic"
    / "versions"
    / "0b68f51fe976_creation_des_tables_epic23.py"
)

VALID_SECRET = (
    "aZ3kLm9Qp2Rt7Vx4Bc8Nd1Fg6Hj5Ws0Ye3Ur9Iv2Ot8Pq4Lm7Kd1Jf6"
)

EXPECTED_TABLES = {
    "users",
    "guest_sessions",
    "conversations",
    "conversation_profiles",
    "messages",
}


def _run_python(code: str, **overrides: str) -> subprocess.CompletedProcess:
    """Exécuter du code dans un sous-processus avec un environnement isolé."""
    env = os.environ.copy()
    for name in (
        "JWT_SECRET",
        "APP_ENV",
        "ENVIRONMENT",
        "ENV",
        "DATABASE_URL",
    ):
        env.pop(name, None)
    env["DATABASE_URL"] = "sqlite://"
    env.update(overrides)
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


# ---------------------------------------------------------------------------
# 1. JWT : validation du secret
# ---------------------------------------------------------------------------


def test_secret_absent_refuse_en_production():
    with pytest.raises(RuntimeError, match="JWT_SECRET est obligatoire"):
        validate_secret_key(None, production=True)


@pytest.mark.parametrize("value", ["", "   ", "\n\t"])
def test_secret_vide_refuse_en_production(value):
    with pytest.raises(RuntimeError, match="JWT_SECRET est obligatoire"):
        validate_secret_key(value, production=True)


def test_secret_trop_court_refuse():
    with pytest.raises(RuntimeError, match="longueur minimale"):
        validate_secret_key("A1b2C3d4E5f6G7h8", production=False)


def test_secret_placeholder_refuse():
    with pytest.raises(RuntimeError, match="placeholder"):
        validate_secret_key("change_me_with_a_long_random_string", production=False)


def test_secret_entropie_insuffisante_refusee():
    with pytest.raises(RuntimeError, match="entropie"):
        validate_secret_key("a" * (MIN_SECRET_KEY_LENGTH + 8), production=False)


def test_secret_valide_est_accepte():
    assert validate_secret_key(VALID_SECRET, production=True) == VALID_SECRET


def test_secret_absent_en_developpement_genere_une_cle_ephemere():
    with pytest.warns(RuntimeWarning):
        first = validate_secret_key(None, production=False)
    with pytest.warns(RuntimeWarning):
        second = validate_secret_key(None, production=False)

    assert len(first) >= MIN_SECRET_KEY_LENGTH
    assert len(set(first)) >= 8
    assert first != second


def test_demarrage_refuse_sans_jwt_secret_en_production():
    result = _run_python(
        "import app.core.security",
        APP_ENV="production",
    )

    assert result.returncode != 0
    assert "JWT_SECRET est obligatoire en production" in result.stderr


def test_demarrage_refuse_un_secret_faible_sans_le_divulguer():
    canary = "LEAK_CANARY_123"
    result = _run_python(
        "import app.core.security",
        APP_ENV="production",
        JWT_SECRET=canary,
    )

    assert result.returncode != 0
    assert "JWT_SECRET invalide" in result.stderr
    assert canary not in result.stderr
    assert canary not in result.stdout


def test_demarrage_developpement_sans_jwt_secret_est_tolere():
    result = _run_python(
        "import app.core.security; print('OK')",
        APP_ENV="development",
    )

    assert result.returncode == 0
    assert "OK" in result.stdout


# ---------------------------------------------------------------------------
# 2. Alembic : complétude de target_metadata
# ---------------------------------------------------------------------------


def test_target_metadata_contient_les_cinq_tables():
    from app.db.base import Base
    import app.db.models  # noqa: F401  (enregistre les tables dans Base.metadata)

    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_les_tables_du_metadata_correspondent_a_la_migration():
    from app.db.base import Base
    import app.db.models  # noqa: F401

    migration_sql = MIGRATION_FILE.read_text(encoding="utf-8")
    migration_tables = set(
        re.findall(r"op\.create_table\(\s*['\"]([^'\"]+)", migration_sql)
    )

    assert migration_tables == EXPECTED_TABLES
    assert set(Base.metadata.tables) == migration_tables


def test_alembic_charge_le_metadata_complet():
    """``app.db.models`` doit exposer les cinq modèles."""
    from app.db import models

    assert set(models.__all__) == {
        "User",
        "GuestSession",
        "Conversation",
        "ConversationProfile",
        "Message",
    }
    assert models.User.__tablename__ == "users"
    assert models.GuestSession.__tablename__ == "guest_sessions"
    assert models.Conversation.__tablename__ == "conversations"
    assert (
        models.ConversationProfile.__tablename__ == "conversation_profiles"
    )
    assert models.Message.__tablename__ == "messages"


# ---------------------------------------------------------------------------
# 3. Route de debug
# ---------------------------------------------------------------------------


def test_route_debug_presente_hors_production():
    from app.main import app

    assert "/test-error" in app.openapi()["paths"]


def test_route_debug_absente_en_production():
    code = (
        "from app.main import app\n"
        "paths = app.openapi()['paths']\n"
        "assert '/test-error' not in paths\n"
        "assert '/api/formations' in paths\n"
        "print(len(paths))\n"
    )
    result = _run_python(
        code,
        APP_ENV="production",
        JWT_SECRET=VALID_SECRET,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "17"
