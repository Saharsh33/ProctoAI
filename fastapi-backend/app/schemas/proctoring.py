import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProctoringLogBase(BaseModel):
    email: str
    name: str
    test_id: str
    voice_db: int = 0
    img_log: str
    user_movements_updown: int
    user_movements_lr: int
    user_movements_eyes: int
    phone_detection: int
    person_status: int
    uid: uuid.UUID


class ProctoringLogCreate(ProctoringLogBase):
    pass


class ProctoringLogOut(ProctoringLogBase):
    model_config = ConfigDict(from_attributes=True)

    pid: int
    log_time: datetime


# ── Violation schemas (Sprint 2 + Sprint 3 enhancements) ──


class ViolationBase(BaseModel):
    email: str
    test_id: str
    violation_type: str  # tab_switch | face_absent | multiple_faces | audio_violation | identity_mismatch
    message: str
    severity: str = "warning"  # info | warning | critical
    metadata_json: str | None = None
    evidence_url: str | None = None  # S3/MinIO object URL (Sprint 3)
    uid: uuid.UUID


class ViolationCreate(ViolationBase):
    pass


class ViolationOut(ViolationBase):
    model_config = ConfigDict(from_attributes=True)

    vid: int
    created_at: datetime


# ── Batch violation schemas (Sprint 3 – async batch writes) ──


class ViolationBatchItem(BaseModel):
    """Single item in a batch violation request."""

    email: str
    test_id: str
    violation_type: str
    message: str
    severity: str = "warning"
    metadata_json: str | None = None
    evidence_url: str | None = None
    uid: uuid.UUID


class ViolationBatchCreate(BaseModel):
    """Batch of violations sent at once."""

    violations: list[ViolationBatchItem]


class ViolationBatchResponse(BaseModel):
    """Response for batch violation endpoint."""

    accepted: int
    buffered: bool
    message: str


# ── Presigned URL schemas (Sprint 3 – evidence upload) ──


class EvidenceUploadRequest(BaseModel):
    """Request a presigned PUT URL for uploading screenshot evidence."""

    test_id: str
    email: str
    violation_type: str
    timestamp_ms: int


class EvidenceUploadResponse(BaseModel):
    """Presigned URL + metadata for client-side upload."""

    upload_url: str
    object_key: str
    object_url: str
