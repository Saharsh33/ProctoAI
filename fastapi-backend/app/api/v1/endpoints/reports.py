"""
Report API endpoints (Sprint 4 – REQ-11, REQ-12).

Provides:
  GET  /reports/trust-score          – compute trust score without persisting
  POST /reports/generate             – generate full report (trust + PDF)
  GET  /reports/                     – list reports
  GET  /reports/{report_id}          – get single report
  GET  /reports/{report_id}/pdf      – download PDF
"""

import logging
import uuid as _uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import crud
from app.api.deps import get_db
from app.schemas.report import (
    ExamReportCreate,
    ExamReportOut,
    ExamReportSummary,
    TrustScoreRequest,
    TrustScoreResponse,
)
from app.services.report_generator import generate_report
from app.services.trust_score import calculate_trust_score

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


# ── Trust Score (standalone, no persistence) ──────────


@router.post("/trust-score", response_model=TrustScoreResponse)
def compute_trust_score(
    payload: TrustScoreRequest,
    db: Session = Depends(get_db),
):
    """Compute and return the trust score without generating a full report."""
    logger.info(
        "Computing trust score: test_id=%s, email=%s", payload.test_id, payload.email
    )
    result = calculate_trust_score(db, payload.test_id, payload.email)
    logger.info(
        "Trust score computed: score=%d, violations=%d",
        result["trust_score"],
        result["total_violations"],
    )
    return TrustScoreResponse(**result)


# ── Generate Report (trust + PDF) ─────────────────────


@router.post("/generate", response_model=ExamReportOut, status_code=201)
def generate_exam_report(
    payload: ExamReportCreate,
    db: Session = Depends(get_db),
):
    """
    Generate a full proctoring report:
    1. Calculate trust score from violations
    2. Build summary text
    3. Persist ExamReport row
    4. Render PDF via ReportLab
    Target: < 2 s.
    """
    logger.info(
        "Generating report: test_id=%s, email=%s, uid=%s",
        payload.test_id,
        payload.email,
        payload.uid,
    )
    # Optionally look up exam title (test_id is a string UUID)
    exam_title = ""
    try:
        exam = crud.get_exam_by_id(db, _uuid.UUID(payload.test_id))
        if exam:
            exam_title = exam.title
    except (ValueError, AttributeError):
        logger.debug("Could not resolve exam title for test_id=%s", payload.test_id)

    report = generate_report(
        db,
        test_id=payload.test_id,
        email=payload.email,
        uid=str(payload.uid),
        exam_title=exam_title,
    )
    logger.info(
        "Report generated: report_id=%s, trust_score=%s",
        report.report_id,
        report.trust_score,
    )
    return report


# ── List Reports ──────────────────────────────────────


@router.get("/", response_model=list[ExamReportSummary])
def list_reports(
    test_id: str | None = None,
    email: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    logger.info(
        "Listing reports: test_id=%s, email=%s, skip=%d, limit=%d",
        test_id,
        email,
        skip,
        limit,
    )
    reports = crud.list_reports(
        db, test_id=test_id, email=email, skip=skip, limit=limit
    )
    logger.debug("Returned %d reports", len(reports))
    return reports


# ── Get Single Report ─────────────────────────────────


@router.get("/{report_id}", response_model=ExamReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    logger.info("Fetching report: id=%d", report_id)
    report = crud.get_report_by_id(db, report_id)
    if not report:
        logger.warning("Report not found: id=%d", report_id)
        raise HTTPException(status_code=404, detail="Report not found")
    return report


# ── Download PDF ──────────────────────────────────────


@router.get("/{report_id}/pdf")
def download_report_pdf(report_id: int, db: Session = Depends(get_db)):
    """Stream the generated PDF file for download."""
    logger.info("PDF download requested: report_id=%d", report_id)
    report = crud.get_report_by_id(db, report_id)
    if not report:
        logger.warning("Report not found for PDF download: id=%d", report_id)
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.pdf_path:
        logger.warning("PDF not yet generated for report: id=%d", report_id)
        raise HTTPException(status_code=404, detail="PDF not generated yet")

    pdf_path = Path(report.pdf_path)
    if not pdf_path.exists():
        logger.error("PDF file missing on disk: path=%s", report.pdf_path)
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    logger.info("Serving PDF: path=%s", pdf_path)
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )
