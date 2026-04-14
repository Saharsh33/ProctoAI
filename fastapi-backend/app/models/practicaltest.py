from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PracticalTest(Base):
    __tablename__ = "practicaltest"

    pid: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    test_id: Mapped[str] = mapped_column(String(100), nullable=False)
    qid: Mapped[str] = mapped_column(String(25), nullable=False)
    code: Mapped[str | None] = mapped_column(Text, nullable=True)
    input: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed: Mapped[str | None] = mapped_column(String(125), nullable=True)
    marks: Mapped[int] = mapped_column(Integer, nullable=False)

    uid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    user = relationship("User", back_populates="practicaltests")
