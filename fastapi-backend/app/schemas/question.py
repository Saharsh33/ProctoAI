import uuid

from pydantic import BaseModel, ConfigDict


class QuestionBase(BaseModel):
    qid: str
    q: str
    a: str
    b: str
    c: str
    d: str
    ans: str
    marks: int
    uid: uuid.UUID
    examId: uuid.UUID | None = None


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    test_id: str | None = None
    qid: str | None = None
    q: str | None = None
    a: str | None = None
    b: str | None = None
    c: str | None = None
    d: str | None = None
    ans: str | None = None
    marks: int | None = None
    uid: uuid.UUID | None = None
    examId: uuid.UUID | None = None


class QuestionOut(QuestionBase):
    model_config = ConfigDict(from_attributes=True)
    questions_uid: int
