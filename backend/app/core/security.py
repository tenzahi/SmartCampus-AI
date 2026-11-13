"""Sécurité JWT et hachage des mots de passe (US27).

La clé de signature provient exclusivement de la variable d'environnement
``JWT_SECRET``. Aucun secret n'est codé en dur, affiché ou journalisé.

Règles :
- en production, l'absence de ``JWT_SECRET`` interrompt le démarrage ;
- une clé fournie mais trop courte, trop peu variée ou correspondant à un
  placeholder public est refusée dans tous les environnements ;
- hors production uniquement, une clé éphémère aléatoire est générée quand
  ``JWT_SECRET`` est absent, ce qui invalide les tokens à chaque redémarrage.
"""

import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.environment import is_production

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

MIN_SECRET_KEY_LENGTH = 32
MIN_DISTINCT_CHARACTERS = 8

# Placeholders publics et anciens fallbacks : jamais acceptés.
REJECTED_SECRET_KEYS = frozenset(
    {
        "une_cle_secrete_tres_complexe_smartcampus_2026",
        "change_me_with_a_long_random_string",
        "changeme",
        "change-me",
        "secret",
        "smartcampus",
    }
)

password_hash = PasswordHash.recommended()


def validate_secret_key(
    secret_key: Optional[str],
    *,
    production: bool,
) -> str:
    """Valider ``JWT_SECRET`` et retourner une clé exploitable.

    Le message d'erreur ne contient jamais la valeur fournie.
    """
    if secret_key is None or not secret_key.strip():
        if production:
            raise RuntimeError(
                "JWT_SECRET est obligatoire en production. "
                "Définissez une clé aléatoire d'au moins "
                f"{MIN_SECRET_KEY_LENGTH} caractères."
            )
        warnings.warn(
            "JWT_SECRET est absent : une clé éphémère est générée pour cet "
            "environnement de développement. Les tokens seront invalidés à "
            "chaque redémarrage. Définissez JWT_SECRET pour les conserver.",
            RuntimeWarning,
            stacklevel=2,
        )
        return secrets.token_urlsafe(48)

    value = secret_key.strip()

    if len(value) < MIN_SECRET_KEY_LENGTH:
        raise RuntimeError(
            "JWT_SECRET invalide : longueur minimale "
            f"{MIN_SECRET_KEY_LENGTH} caractères."
        )

    if value.lower() in REJECTED_SECRET_KEYS:
        raise RuntimeError(
            "JWT_SECRET invalide : valeur placeholder ou publique refusée."
        )

    if len(set(value)) < MIN_DISTINCT_CHARACTERS:
        raise RuntimeError(
            "JWT_SECRET invalide : entropie insuffisante, utilisez une clé "
            "aléatoire."
        )

    return value


SECRET_KEY = validate_secret_key(
    os.getenv("JWT_SECRET"),
    production=is_production(),
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def create_access_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
