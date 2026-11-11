import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func, Index, text
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class GuestSession(Base):
    __tablename__ = "guest_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    guest_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default=text("'active'"))
    claimed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String)

    __table_args__ = (
        Index("idx_guest_sessions_expires", "expires_at", postgresql_where=text("status = 'active'")),
        Index("idx_guest_sessions_ip", "ip_address", "created_at"),
    )