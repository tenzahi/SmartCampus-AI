import secrets
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, cast, text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Session
from app.db.models import GuestSession
from app.core.config import settings
from app.db.models import Conversation


def is_guest_session_expired(
    expires_at: datetime,
    now: datetime | None = None,
) -> bool:
    current_time = now or datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    return expires_at <= current_time


def hash_token(token: str) -> str:
    """Hash le token en SHA-256 (on ne stocke jamais le token en clair !)."""
    return hashlib.sha256(token.encode()).hexdigest()

def generate_guest_token() -> tuple[str, str]:
    """Génère un token aléatoire et son hash."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def cleanup_expired_guest_sessions(
    db: Session,
    *,
    now: datetime | None = None,
    batch_size: int = 100,
) -> int:
    """Delete expired anonymous data while retaining claimed transcripts."""
    if batch_size < 1:
        raise ValueError("batch_size doit être supérieur à zéro.")

    cutoff = now or datetime.now(timezone.utc)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    sessions = db.scalars(
        select(GuestSession)
        .where(GuestSession.expires_at <= cutoff)
        .order_by(GuestSession.expires_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    ).all()
    if not sessions:
        return 0

    session_ids = [session.id for session in sessions]
    conversations = db.scalars(
        select(Conversation).where(
            Conversation.guest_session_id.in_(session_ids)
        )
    ).all()
    by_session: dict[uuid.UUID, list[Conversation]] = {
        session_id: [] for session_id in session_ids
    }
    for conversation in conversations:
        if conversation.guest_session_id is not None:
            by_session.setdefault(conversation.guest_session_id, []).append(
                conversation
            )

    try:
        for session in sessions:
            linked_conversations = by_session.get(session.id, [])
            if session.status == "active":
                for conversation in linked_conversations:
                    if conversation.candidate_id is None:
                        db.delete(conversation)
            elif session.status == "claimed":
                if any(
                    conversation.candidate_id is None
                    for conversation in linked_conversations
                ):
                    raise RuntimeError(
                        "Une session revendiquée contient une conversation "
                        "sans propriétaire candidat."
                    )
            else:
                raise RuntimeError(
                    f"Statut de session visiteur inattendu : {session.status}."
                )
            db.delete(session)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return len(sessions)


def create_guest_session(db: Session, ip_address: str | None = None, user_agent: str | None = None) -> dict:
    """Crée une nouvelle session visiteur."""

    cleanup_expired_guest_sessions(db)

    # 1. Vérifier la limite anti-abus par IP (max 5 par jour)
    if ip_address:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(
                text(
                    "SELECT pg_advisory_xact_lock("
                    "hashtextextended(:lock_key, 0))"
                ),
                {"lock_key": f"guest-session-create:{ip_address}"},
            )

        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        count_query = select(func.count()).select_from(GuestSession).where(
            GuestSession.ip_address == cast(ip_address, INET),
            GuestSession.created_at > one_day_ago
        )
        count = db.scalar(count_query)
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
    db.commit()
    db.refresh(new_session)

    # 4. Retourner le token EN CLAIR au client (une seule fois !)
    return {
        "guest_session_id": str(session_id),
        "guest_token": token,
        "expires_at": expires_at.isoformat()
    }

def validate_guest_session(db: Session, session_id: str, token: str) -> GuestSession | None:
    """Vérifie qu'une session est valide (existe, active, non expirée, bon token)."""
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        return None

    query = select(GuestSession).where(GuestSession.id == session_uuid)
    result = db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        return None
    if session.status != "active":
        return None
    if is_guest_session_expired(session.expires_at):
        return None
    if not secrets.compare_digest(session.guest_token_hash, hash_token(token)):
        return None
        
    return session

def validate_claimed_guest_session(
    db: Session,
    session_id: str,
    token: str,
    candidate_id: int,
) -> GuestSession | None:
    session = validate_guest_session_for_status(db, session_id, token)
    if session and session.status == "claimed" and session.claimed_by == candidate_id:
        return session
    return None


def validate_guest_session_for_status(
    db: Session,
    session_id: str,
    token: str,
) -> GuestSession | None:
    try:
        session_uuid = uuid.UUID(session_id)
    except (TypeError, ValueError):
        return None
    session = db.scalar(select(GuestSession).where(GuestSession.id == session_uuid))
    if not session:
        return None
    if session.status not in {"active", "claimed"}:
        return None
    if is_guest_session_expired(session.expires_at):
        return None
    if not secrets.compare_digest(session.guest_token_hash, hash_token(token)):
        return None
    return session

def claim_guest_session(db: Session, session_id: str, token: str, candidate_id: int, consent: bool) -> dict:
    """Rattache atomiquement une session anonyme à un compte candidat."""
    
    if not consent:
        raise ValueError("Le consentement explicite est requis pour rattacher cette conversation.")

    try:
        session_uuid = uuid.UUID(session_id)
    except (TypeError, ValueError):
        raise ValueError("Session invalide ou expirée")

    # Verrouillage PostgreSQL pour empêcher deux rattachements concurrents.
    session = db.scalar(
        select(GuestSession)
        .where(GuestSession.id == session_uuid)
        .with_for_update()
    )
    if not session:
        raise ValueError("Session invalide ou expirée")
    if session.status != "active":
        raise ValueError("Cette session a déjà été rattachée à un compte.")
    if is_guest_session_expired(session.expires_at):
        raise ValueError("Session invalide ou expirée")
    if not secrets.compare_digest(session.guest_token_hash, hash_token(token)):
        raise ValueError("Session invalide ou expirée")
    if session.claimed_by is not None and session.claimed_by != candidate_id:
        raise ValueError("Cette session appartient à un autre candidat.")

    # 2. Mettre à jour la session
    conversations = db.scalars(
        select(Conversation).where(Conversation.guest_session_id == session.id)
    ).all()
    if not conversations:
        raise ValueError("Cette session ne contient aucune conversation à rattacher.")

    session.claimed_by = candidate_id
    session.status = "claimed"
    session.claimed_at = datetime.now(timezone.utc)
    for conversation in conversations:
        if conversation.candidate_id not in (None, candidate_id):
            raise ValueError("Cette conversation appartient à un autre candidat.")
        conversation.candidate_id = candidate_id

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "status": "claimed",
        "guest_session_id": str(session.id),
        "conversation_ids": [str(conversation.id) for conversation in conversations],
    }