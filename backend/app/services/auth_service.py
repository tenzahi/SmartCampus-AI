from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User
from app.core.security import get_password_hash, verify_password, create_access_token

async def register_user(db: AsyncSession, email: str, password: str, full_name: str):
    # Vérifier si l'email existe déjà
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise ValueError("Cet email est déjà utilisé.")
    
    new_user = User(
        email=email,
        password_hash=get_password_hash(password),
        full_name=full_name,
        role="candidate" # Par défaut, on s'inscrit en tant que candidat
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("Email ou mot de passe incorrect.")
    
    # Génération du JWT avec l'ID et le rôle
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer", "role": user.role}