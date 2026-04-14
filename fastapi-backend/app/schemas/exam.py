import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.exam import ExamStatus


class ExamCreate(BaseModel):
    title: str
    duration: int
    startTime: datetime
    rules: str
    status: ExamStatus = ExamStatus.DRAFT


class ExamUpdate(BaseModel):
    title: str | None = None
    duration: int | None = None
    startTime: datetime | None = None
    rules: str | None = None
    status: ExamStatus | None = None


class ExamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    examId: uuid.UUID
    title: str
    duration: int
    startTime: datetime
    rules: str
    status: ExamStatus
    createdBy: uuid.UUID | None = None
