from fastapi import APIRouter, Depends, Request, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.guest_session_service import create_guest_session, validate_guest_session
from pydantic import BaseModel
from app.services.guest_session_service import claim_guest_session


router = APIRouter(prefix="/api/chat/sessions", tags=["Chat Sessions"])

@router.post("", status_code=201)
async def create_session(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Créer une session visiteur (pas besoin de compte)."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    try:
        result = await create_guest_session(db, ip_address=ip, user_agent=user_agent)
        return result
    except ValueError as e:
        raise HTTPException(status_code=429, detail=str(e))

@router.get("/me")
async def get_my_session(
    x_guest_session: str = Header(...),
    x_guest_token: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """Vérifier sa session."""
    session = await validate_guest_session(db, x_guest_session, x_guest_token)
    if not session:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée")
    
    return {
        "guest_session_id": str(session.id),
        "status": session.status,
        "expires_at": session.expires_at.isoformat()
    }
    
class ClaimRequest(BaseModel):
    guest_token: str
    consent: bool
    candidate_id: int  # Normalement on le récupère du JWT (Auth), ici on le passe pour le test

@router.post("/{session_id}/claim")
async def claim_session(
    session_id: str,
    payload: ClaimRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await claim_guest_session(
            db=db,
            session_id=session_id,
            token=payload.guest_token,
            candidate_id=payload.candidate_id,
            consent=payload.consent
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))