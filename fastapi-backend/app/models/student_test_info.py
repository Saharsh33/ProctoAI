from __future__ import annotations

import uuid
from datetime import time

from sqlalchemy import ForeignKey, SmallInteger, String, Time, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StudentTestInfo(Base):
    __tablename__ = "studenttestinfo"

    stiid: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    test_id: Mapped[str] = mapped_column(String(100), nullable=False)
    time_left: Mapped[time] = mapped_column(Time, nullable=False)
    completed: Mapped[int] = mapped_column(
        SmallInteger, server_default="0", nullable=False
    )

    uid: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    user = relationship("User", back_populates="student_test_infos")
