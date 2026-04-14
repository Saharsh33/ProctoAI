from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Teacher(Base):
    __tablename__ = "teachers"

    tid: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    test_id: Mapped[str] = mapped_column(String(100), nullable=False)
    test_type: Mapped[str] = mapped_column(String(75), nullable=False)
    start: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    end: Mapped[datetime] = mapped_column("end", DateTime, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    show_ans: Mapped[int] = mapped_column(Integer, nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    neg_marks: Mapped[int] = mapped_column(Integer, nullable=False)
    calc: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    proctoring_type: Mapped[int] = mapped_column(
        SmallInteger, server_default="0", nullable=False
    )

    uid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    user = relationship("User", back_populates="teachers")
