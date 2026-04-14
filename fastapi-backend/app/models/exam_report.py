"""ExamReport model – stores generated proctoring reports (Sprint 4)."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.db.base import Base
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ExamReport(Base):
    """One report per (student, exam) pair.  Generated after exam submission."""

    __tablename__ = "exam_reports"

    report_id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # ── Aggregated scores ──────────────────────────
    trust_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    total_violations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    penalty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Exam marks ─────────────────────────────────
    obtained_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── JSON blobs for the full breakdown ──────────
    violation_breakdown_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # e.g. [{"type":"tab_switch","count":3,"weight":20,"subtotal":60}, ...]

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Human-readable summary paragraph

    # ── PDF storage path (relative or URL) ─────────
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ─────────────────────────────────
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # ── FK to user ─────────────────────────────────
    uid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    user = relationship("User", back_populates="exam_reports")
