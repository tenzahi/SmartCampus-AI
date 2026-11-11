import secrets
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, cast
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import GuestSession
from app.config import settings

def hash_token(token: str) -> str:
    """Hash le token en SHA-256 (on ne stocke jamais le token en clair !)."""
    return hashlib.sha256(token.encode()).hexdigest()

def generate_guest_token() -> tuple[str, str]:
    """Génère un token aléatoire et son hash."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)

async def create_guest_session(db: AsyncSession, ip_address: str | None = None, user_agent: str | None = None) -> dict:
    """Crée une nouvelle session visiteur."""
    
    # 1. Vérifier la limite anti-abus par IP (max 5 par jour)
    if ip_address:
        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        count_query = select(func.count()).select_from(GuestSession).where(
            GuestSession.ip_address == cast(ip_address, INET),
            GuestSession.created_at > one_day_ago
        )
        count = await db.scalar(count_query)
        if count and count >= settings.guest_session_max_per_ip:
            raise ValueError("Trop de sessions créées depuis cette adresse IP. Réessayez plus tard.")

    # 2. Générer le token et calculer l'expiration
    token, token_hash = generate_guest_token()
    session_id = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.guest_session_ttl_hours)

    # 3. Sauvegarder en base
    new_session = GuestSession(
        id=session_id,
        guest_token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    # 4. Retourner le token EN CLAIR au client (une seule fois !)
    return {
        "guest_session_id": str(session_id),
        "guest_token": token,
        "expires_at": expires_at.isoformat()
    }

async def validate_guest_session(db: AsyncSession, session_id: str, token: str) -> GuestSession | None:
    """Vérifie qu'une session est valide (existe, active, non expirée, bon token)."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        return None

    query = select(GuestSession).where(GuestSession.id == session_uuid)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        return None
    if session.status != "active":
        return None
    if session.expires_at < datetime.now(timezone.utc):
        return None
    if not secrets.compare_digest(session.guest_token_hash, hash_token(token)):
        return None
        
    return session