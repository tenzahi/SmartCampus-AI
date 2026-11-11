from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.auth_service import register_user, authenticate_user
from app.schemas.auth import UserRegister, Token
from app.core.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/auth", tags=["Authentification"])

@router.post("/register", status_code=201)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(db, payload.email, payload.password, payload.full_name)
        return {"message": "Compte créé avec succès", "user_id": user.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    try:
        # OAuth2 utilise "username" pour l'email
        return await authenticate_user(db, form_data.username, form_data.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Route protégée pour tester si le JWT fonctionne."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "full_name": current_user.full_name
    }