import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class TeacherBase(BaseModel):
    email: EmailStr
    test_id: str
    test_type: str
    start: datetime | None = None
    end: datetime
    duration: int
    show_ans: int
    password: str
    subject: str
    topic: str
    neg_marks: int
    calc: int
    proctoring_type: int = 0
    uid: uuid.UUID


class TeacherCreate(TeacherBase):
    pass


class TeacherOut(TeacherBase):
    model_config = ConfigDict(from_attributes=True)
    tid: int
