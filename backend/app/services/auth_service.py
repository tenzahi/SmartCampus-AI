"""Services d'inscription et d'authentification (US27, version synchrone)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.db.models import User


def register_user(
    db: Session,
    email: str,
    password: str,
    full_name: str,
) -> User:
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise ValueError("Cet email est déjà utilisé.")

    new_user = User(
        email=email,
        password_hash=get_password_hash(password),
        full_name=full_name,
        role="candidate",
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Cet email est déjà utilisé.")
    db.refresh(new_user)
    return new_user


def authenticate_user(db: Session, email: str, password: str) -> dict:
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("Email ou mot de passe incorrect.")

    if not user.is_active:
        raise ValueError("Compte désactivé.")

    token = create_access_token(
        data={"sub": str(user.id), "role": user.role}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
    }
