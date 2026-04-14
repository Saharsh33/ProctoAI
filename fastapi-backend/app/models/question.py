from __future__ import annotations

import uuid

from app.db.base import Base
from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Question(Base):
    __tablename__ = "questions"

    questions_uid: Mapped[int] = mapped_column(primary_key=True)
    examId: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("exams.examId"), nullable=True, index=True
    )
    qid: Mapped[str] = mapped_column(String(25), nullable=False)
    q: Mapped[str] = mapped_column(Text, nullable=False)
    a: Mapped[str] = mapped_column(String(100), nullable=False)
    b: Mapped[str] = mapped_column(String(100), nullable=False)
    c: Mapped[str] = mapped_column(String(100), nullable=False)
    d: Mapped[str] = mapped_column(String(100), nullable=False)
    ans: Mapped[str] = mapped_column(String(10), nullable=False)
    marks: Mapped[int] = mapped_column(Integer, nullable=False)

    uid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    user = relationship("User", back_populates="questions")
    exam = relationship("Exam", back_populates="questions")
