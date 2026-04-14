import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WindowEventBase(BaseModel):
    email: str
    test_id: str
    name: str
    window_event: int
    uid: uuid.UUID


class WindowEventCreate(WindowEventBase):
    pass


class WindowEventOut(WindowEventBase):
    model_config = ConfigDict(from_attributes=True)

    wid: int
    transaction_log: datetime
