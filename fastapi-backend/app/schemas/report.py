"""Schemas for Exam Reports and Trust Score (Sprint 4 – REQ-11, REQ-12)."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


# ── Trust Score ────────────────────────────────────────

class TrustScoreBreakdownItem(BaseModel):
    type: str
    count: int
    weight: int
    subtotal: int


class TrustScoreResponse(BaseModel):
    trust_score: int
    penalty: int
    total_violations: int
    breakdown: list[TrustScoreBreakdownItem]


class TrustScoreRequest(BaseModel):
    test_id: str
    email: str


# ── Exam Report ────────────────────────────────────────

class ExamReportCreate(BaseModel):
    test_id: str
    email: str
    uid: uuid.UUID


class ExamReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: int
    test_id: str
    email: str
    trust_score: int
    total_violations: int
    penalty: int
    obtained_marks: int
    total_marks: int
    violation_breakdown_json: str | None = None
    summary: str | None = None
    pdf_path: str | None = None
    generated_at: datetime
    uid: uuid.UUID


class ExamReportSummary(BaseModel):
    """Lightweight list item."""
    model_config = ConfigDict(from_attributes=True)

    report_id: int
    test_id: str
    email: str
    trust_score: int
    total_violations: int
    obtained_marks: int
    total_marks: int
    generated_at: datetime
