from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Violation(Base):
    """Violation record logged by the live proctoring engine."""

    __tablename__ = "violations"

    vid: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    test_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    violation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. tab_switch, face_absent, multiple_faces, audio_violation, identity_mismatch
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), server_default="warning", nullable=False
    )
    # info | warning | critical
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # S3/MinIO object URL for screenshot evidence (Sprint 3)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    uid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    user = relationship("User", back_populates="violations")
