from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from app.db.base import Base
from app.models.enums import RoleEnum
from sqlalchemy import DateTime, Enum, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.admin_action import AdminAction
    from app.models.exam_report import ExamReport
    from app.models.longqa import LongQA
    from app.models.longtest import LongTest
    from app.models.practicalqa import PracticalQA
    from app.models.practicaltest import PracticalTest
    from app.models.proctoring_log import ProctoringLog
    from app.models.question import Question
    from app.models.student import Student
    from app.models.student_test_info import StudentTestInfo
    from app.models.teacher import Teacher
    from app.models.violation import Violation
    from app.models.window_estimation_log import WindowEstimationLog


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), nullable=False)
    user_image: Mapped[str] = mapped_column(Text, nullable=False)
    user_login: Mapped[int] = mapped_column(Integer, nullable=False)
    examcredits: Mapped[int] = mapped_column(
        Integer, server_default="7", nullable=False
    )

    teachers: Mapped[List["Teacher"]] = relationship(back_populates="user")
    questions: Mapped[List["Question"]] = relationship(back_populates="user")
    students: Mapped[List["Student"]] = relationship(back_populates="user")
    student_test_infos: Mapped[List["StudentTestInfo"]] = relationship(
        back_populates="user"
    )
    proctoring_logs: Mapped[List["ProctoringLog"]] = relationship(back_populates="user")
    window_logs: Mapped[List["WindowEstimationLog"]] = relationship(
        back_populates="user"
    )
    violations: Mapped[List["Violation"]] = relationship(back_populates="user")
    exam_reports: Mapped[List["ExamReport"]] = relationship(back_populates="user")
    admin_actions: Mapped[List["AdminAction"]] = relationship(
        back_populates="admin_user"
    )
    longqas: Mapped[List["LongQA"]] = relationship(back_populates="user")
    longtests: Mapped[List["LongTest"]] = relationship(back_populates="user")
    practicalqas: Mapped[List["PracticalQA"]] = relationship(back_populates="user")
    practicaltests: Mapped[List["PracticalTest"]] = relationship(back_populates="user")
