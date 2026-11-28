from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from redis import Redis
from app.db.session import get_db
from app.db.redis_client import get_redis
from app.core.dependencies import ensure_token_not_revoked
from app.core.config import settings
from app.services.chat_service import (
    ChatMessageLimitExceeded,
    handle_chat_message,
)
from app.core.security import decode_access_token
from sqlalchemy import select
from app.db.models import User

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=settings.chat_message_max_length,
    )

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, message: str) -> str:
        if not message.strip():
            raise ValueError("Le message ne peut pas être vide.")
        return message

@router.post("")
def chat(
    payload: ChatRequest,
    x_guest_session: str = Header(default=None),
    x_guest_token: str = Header(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    try:
        candidate_id = None
        if authorization:
            scheme, _, token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not token:
                raise HTTPException(status_code=401, detail="Token invalide ou expiré")
            claims = decode_access_token(token)
            if not claims:
                raise HTTPException(status_code=401, detail="Token invalide ou expiré")
            ensure_token_not_revoked(claims, redis)
            try:
                candidate_id = int(claims["sub"])
            except (KeyError, TypeError, ValueError):
                raise HTTPException(status_code=401, detail="Token invalide ou expiré")
            user = db.scalar(select(User).where(User.id == candidate_id))
            if user is None or not user.is_active or user.role != "candidate":
                raise HTTPException(status_code=403, detail="Accès candidat requis")

        if not x_guest_session or not x_guest_token:
            raise HTTPException(status_code=401, detail="Session visiteur requise")
        result = handle_chat_message(
            db=db, 
            redis=redis, 
            guest_session_id=x_guest_session, 
            token=x_guest_token, 
            message=payload.message,
            candidate_id=candidate_id,
        )
        return result
    except ChatMessageLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))