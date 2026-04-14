from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AdminAction(Base):
    """Audit log for admin actions taken on violations (warn / invalidate / ban)."""

    __tablename__ = "admin_actions"

    action_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    violation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("violations.vid"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # warn | invalidate | ban
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    performed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    violation = relationship("Violation", backref="admin_actions")
    admin_user = relationship("User", back_populates="admin_actions")
