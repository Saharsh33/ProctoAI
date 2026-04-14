from __future__ import annotations

import uuid

from app.db.base import Base
from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship


class LongQA(Base):
    __tablename__ = "longqa"

    longqa_qid: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[str] = mapped_column(String(100), nullable=False)
    qid: Mapped[str] = mapped_column(String(25), nullable=False)
    q: Mapped[str] = mapped_column(Text, nullable=False)
    marks: Mapped[int | None] = mapped_column(Integer, nullable=True)

    uid: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=True, index=True
    )
    user = relationship("User", back_populates="longqas")
