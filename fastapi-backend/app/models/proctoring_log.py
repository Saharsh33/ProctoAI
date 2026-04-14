from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProctoringLog(Base):
    __tablename__ = "proctoring_log"

    pid: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    test_id: Mapped[str] = mapped_column(String(100), nullable=False)
    voice_db: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    img_log: Mapped[str] = mapped_column(Text, nullable=False)
    user_movements_updown: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    user_movements_lr: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    user_movements_eyes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    phone_detection: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    person_status: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    log_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    uid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    user = relationship("User", back_populates="proctoring_logs")
