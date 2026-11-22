from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from redis import Redis
from app.db.session import get_db
from app.db.redis_client import get_redis
from app.services.chat_service import handle_chat_message

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str

@router.post("")
def chat(
    payload: ChatRequest,
    x_guest_session: str = Header(...),
    x_guest_token: str = Header(...),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    try:
        result = handle_chat_message(
            db=db, 
            redis=redis, 
            guest_session_id=x_guest_session, 
            token=x_guest_token, 
            message=payload.message
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))