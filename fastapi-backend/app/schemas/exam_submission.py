import uuid
from datetime import datetime
from pydantic import BaseModel


class AnswerSubmission(BaseModel):
    """Schema for a single answer submission."""

    qid: str
    answer: str


class ExamSubmission(BaseModel):
    """Schema for submitting exam answers."""

    examId: uuid.UUID
    answers: list[AnswerSubmission]


class ExamSubmissionResponse(BaseModel):
    """Response after exam submission."""

    message: str
    submitted_count: int
    server_confirmed_at: datetime
