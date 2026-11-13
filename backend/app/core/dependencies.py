"""Dépendances d'authentification et de contrôle de rôle (US27).

Version synchrone alignée sur l'architecture Task20 : elle réutilise
``app.db.session.get_db`` et le moteur SQLAlchemy unique du backend.
"""

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    subject = payload.get("sub")
    if subject is None:
        raise credentials_exception

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise credentials_exception

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé.",
        )
    return user


def require_role(allowed_roles: list[str]):
    """Restreindre une route aux rôles indiqués.

    Exemple :
        current_user: User = Depends(require_role(["admin", "resp_iit"]))
    """

    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> Any:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Accès refusé. Rôles autorisés : "
                    f"{', '.join(allowed_roles)}"
                ),
            )
        return current_user

    return role_checker


# Garde commun aux opérations d'écriture du catalogue Task20.
catalogue_writer = require_role(["admin", "resp_iit", "resp_isb"])
