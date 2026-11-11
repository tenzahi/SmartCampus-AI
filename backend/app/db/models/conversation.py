import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    guest_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("guest_sessions.id", ondelete="SET NULL"))
    candidate_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("guest_session_id IS NOT NULL OR candidate_id IS NOT NULL", name="ck_conversations_has_owner"),
        Index("idx_conversations_guest", "guest_session_id"),
        Index("idx_conversations_candidate", "candidate_id", "updated_at"),
    )