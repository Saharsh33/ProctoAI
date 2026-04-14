from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, SmallInteger, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PracticalQA(Base):
    __tablename__ = "practicalqa"

    pracqa_qid: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[str] = mapped_column(String(100), nullable=False)
    qid: Mapped[str] = mapped_column(String(25), nullable=False)
    q: Mapped[str] = mapped_column(Text, nullable=False)
    compiler: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    marks: Mapped[int] = mapped_column(Integer, nullable=False)

    uid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    user = relationship("User", back_populates="practicalqas")
