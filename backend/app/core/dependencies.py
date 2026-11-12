from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import User
from app.core.security import decode_access_token

# Indique à Swagger où se trouve la route de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ============================================================
# 1. Authentification : Récupérer l'utilisateur connecté via JWT
# ============================================================
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    user = await db.scalar(select(User).where(User.id == int(user_id)))
    if user is None:
        raise credentials_exception
    return user

# ============================================================
# 2. RBAC : Restriction par Rôle (Role-Based Access Control)
# ============================================================
def require_role(allowed_roles: list[str]):
    """
    Dépendance FastAPI pour restreindre l'accès à une route 
    en fonction du rôle de l'utilisateur.

    Exemple d'utilisation dans une route :
        current_user: User = Depends(require_role(["resp_iit", "resp_isb", "admin"]))
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé. Rôles autorisés : {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker