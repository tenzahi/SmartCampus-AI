"""Routes d'authentification US27, adaptées à l'architecture Task20."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import Token, UserRegister
from app.services.auth_service import authenticate_user, register_user


router = APIRouter(prefix="/api/auth", tags=["authentification"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte candidat",
)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    try:
        user = register_user(
            db,
            payload.email,
            payload.password,
            payload.full_name,
        )
        return {"message": "Compte créé avec succès", "user_id": user.id}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/login",
    response_model=Token,
    summary="Se connecter et obtenir un JWT",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    try:
        # OAuth2 utilise le champ « username » pour l'email.
        return authenticate_user(db, form_data.username, form_data.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@router.get(
    "/me",
    summary="Récupérer l'utilisateur connecté",
)
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "full_name": current_user.full_name,
    }
