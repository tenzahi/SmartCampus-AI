import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_candidate
from app.db.models import Conversation, Message, User
from app.db.session import get_db


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
def list_my_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_candidate),
):
    conversations = db.scalars(
        select(Conversation)
        .where(Conversation.candidate_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    ).all()
    return [
        {
            "id": str(conversation.id),
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        }
        for conversation in conversations
    ]


@router.get("/{conversation_id}")
def get_my_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_candidate),
):
    try:
        conversation_uuid = uuid.UUID(conversation_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_uuid,
            Conversation.candidate_id == current_user.id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    ).all()
    return {
        "id": str(conversation.id),
        "title": conversation.title,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in messages
        ],
    }
