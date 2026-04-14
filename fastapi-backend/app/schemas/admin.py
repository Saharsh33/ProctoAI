import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

# ── Admin Action schemas ─────────────────────────────


class AdminActionCreate(BaseModel):
    """Payload for an admin performing an action on a violation."""

    violation_id: int
    action_type: str  # warn | invalidate | ban
    reason: str | None = None


class AdminActionOut(BaseModel):
    """Returned after an admin action is recorded."""

    model_config = ConfigDict(from_attributes=True)

    action_id: int
    violation_id: int
    action_type: str
    reason: str | None = None
    performed_by: uuid.UUID
    performed_at: datetime


# ── Enriched violation view for admin dashboard ──────


class AdminViolationOut(BaseModel):
    """Violation row enriched with action history for the admin table."""

    model_config = ConfigDict(from_attributes=True)

    vid: int
    email: str
    test_id: str
    violation_type: str
    message: str
    severity: str
    metadata_json: str | None = None
    evidence_url: str | None = None
    created_at: datetime
    uid: uuid.UUID
    actions: list[AdminActionOut] = []
