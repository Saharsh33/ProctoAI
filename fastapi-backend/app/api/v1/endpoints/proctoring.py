import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app import crud
from app.schemas.proctoring import (
    ProctoringLogCreate,
    ProctoringLogOut,
    ViolationCreate,
    ViolationOut,
    ViolationBatchCreate,
    ViolationBatchResponse,
    EvidenceUploadRequest,
    EvidenceUploadResponse,
)
from app.services.violation_logger import violation_buffer, classify_violation
from app.core.storage import build_object_key, generate_presigned_put_url, get_public_object_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proctoring", tags=["proctoring"])


# ── Proctoring logs (original) ─────────────────────────

@router.get("/logs", response_model=list[ProctoringLogOut])
def list_logs(
    email: str | None = None,
    test_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    logger.info("Listing proctoring logs: email=%s, test_id=%s, skip=%d, limit=%d", email, test_id, skip, limit)
    logs = crud.list_logs(db, email=email, test_id=test_id, skip=skip, limit=limit)
    logger.debug("Returned %d proctoring logs", len(logs))
    return logs


@router.post("/logs", response_model=ProctoringLogOut, status_code=201)
def create_log(payload: ProctoringLogCreate, db: Session = Depends(get_db)):
    logger.info("Creating proctoring log: email=%s, test_id=%s", payload.email, payload.test_id)
    log = crud.create_proctoring_log(db, payload)
    logger.debug("Proctoring log created: id=%s", log.lid)
    return log


# ── Single violation (immediate write — Sprint 2) ─────

@router.post("/log_violation", response_model=ViolationOut, status_code=201)
def log_violation(payload: ViolationCreate, db: Session = Depends(get_db)):
    """Immediate single-violation write for low-frequency events."""
    logger.info(
        "Logging single violation: email=%s, test_id=%s, type=%s",
        payload.email, payload.test_id, payload.violation_type,
    )
    violation = crud.create_violation(db, payload)
    logger.info("Violation created: id=%s, type=%s", violation.vid, violation.violation_type)
    return violation


# ── Batch violations (async buffered — Sprint 3) ──────

@router.post("/log_violations_batch", response_model=ViolationBatchResponse, status_code=202)
def log_violations_batch(payload: ViolationBatchCreate):
    """
    Accept a batch of violations into the async write buffer.
    The buffer flushes to PostgreSQL every 2 seconds with 3× retry.
    Returns 202 Accepted immediately (< 500 ms target).
    """
    count = len(payload.violations)
    logger.info("Batch violations received: count=%d", count)
    for item in payload.violations:
        violation_buffer.enqueue(item.model_dump())
    logger.debug("Batch enqueued: %d violations, buffer_pending=%d", count, violation_buffer.pending_count)
    return ViolationBatchResponse(
        accepted=count,
        buffered=True,
        message=f"{count} violation(s) accepted into write buffer",
    )


# ── Flush buffer (force write pending violations to DB) ──

@router.post("/flush", status_code=200)
async def flush_violation_buffer():
    """Force-flush all pending violations from the async buffer to the DB.
    Called before report generation to ensure all violations are persisted."""
    logger.info("Manual flush requested, pending=%d", violation_buffer.pending_count)
    count = await violation_buffer._flush()
    logger.info("Manual flush complete: flushed=%d violations", count)
    return {"flushed": count, "message": f"{count} violation(s) flushed to database"}


# ── Violation listing ──────────────────────────────────

@router.get("/violations", response_model=list[ViolationOut])
def list_violations(
    email: str | None = None,
    test_id: str | None = None,
    violation_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    logger.info(
        "Listing violations: email=%s, test_id=%s, type=%s, skip=%d, limit=%d",
        email, test_id, violation_type, skip, limit,
    )
    violations = crud.list_violations(
        db, email=email, test_id=test_id,
        violation_type=violation_type, skip=skip, limit=limit,
    )
    logger.debug("Returned %d violations", len(violations))
    return violations


# ── Evidence upload presigned URL (Sprint 3) ──────────

@router.post("/evidence/upload-url", response_model=EvidenceUploadResponse)
def get_evidence_upload_url(payload: EvidenceUploadRequest):
    """
    Generate a presigned PUT URL so the browser can upload a screenshot
    directly to MinIO (bypasses server bandwidth).
    """
    logger.info(
        "Evidence upload URL requested: test_id=%s, email=%s, type=%s",
        payload.test_id, payload.email, payload.violation_type,
    )
    try:
        object_key = build_object_key(
            test_id=payload.test_id,
            email=payload.email,
            violation_type=payload.violation_type,
            timestamp_ms=payload.timestamp_ms,
        )
        upload_url = generate_presigned_put_url(object_key)
        object_url = get_public_object_url(object_key)
        logger.info("Presigned URL generated: key=%s", object_key)
        return EvidenceUploadResponse(
            upload_url=upload_url,
            object_key=object_key,
            object_url=object_url,
        )
    except Exception as exc:
        logger.error("Failed to generate presigned upload URL: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {exc}")
