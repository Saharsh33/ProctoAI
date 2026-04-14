import uuid
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExamStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"


class Exam(Base):
    __tablename__ = "exams"

    examId: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    startTime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    rules: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[ExamStatus] = mapped_column(
        Enum(ExamStatus), nullable=False, default=ExamStatus.DRAFT
    )
    createdBy: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )

    questions = relationship("Question", back_populates="exam")
    submissions = relationship("Student", back_populates="exam")
