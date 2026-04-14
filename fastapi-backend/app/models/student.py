from __future__ import annotations

import uuid

from app.db.base import Base
from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Student(Base):
    __tablename__ = "students"

    sid: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    test_id: Mapped[str] = mapped_column(String(100), nullable=False)
    examId: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("exams.examId"), nullable=True, index=True
    )
    qid: Mapped[str | None] = mapped_column(String(25), nullable=True)
    ans: Mapped[str | None] = mapped_column(Text, nullable=True)

    uid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    user = relationship("User", back_populates="students")
    exam = relationship("Exam", back_populates="submissions")
