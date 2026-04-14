"""CRUD operations for ExamReport (Sprint 4)."""

from __future__ import annotations

import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.exam_report import ExamReport

logger = logging.getLogger(__name__)


def create(db: Session, **kwargs) -> ExamReport:
    """Insert a new exam report row."""
    report = ExamReport(**kwargs)
    db.add(report)
    db.commit()
    db.refresh(report)
    logger.info(
        "Report created: id=%s, test_id=%s, email=%s, trust_score=%s",
        report.report_id,
        report.test_id,
        report.email,
        report.trust_score,
    )
    return report


def get_by_id(db: Session, report_id: int) -> ExamReport | None:
    report = db.get(ExamReport, report_id)
    logger.debug("Report lookup: id=%s, found=%s", report_id, report is not None)
    return report


def get_by_exam_and_email(db: Session, test_id: str, email: str) -> ExamReport | None:
    """Return the latest report for a student on a specific exam."""
    stmt = (
        select(ExamReport)
        .where(ExamReport.test_id == test_id, ExamReport.email == email)
        .order_by(ExamReport.generated_at.desc())
        .limit(1)
    )
    report = db.execute(stmt).scalar_one_or_none()
    logger.debug(
        "Report lookup by exam+email: test_id=%s, email=%s, found=%s",
        test_id,
        email,
        report is not None,
    )
    return report


def list_reports(
    db: Session,
    test_id: str | None = None,
    email: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[ExamReport]:
    stmt = select(ExamReport)
    if test_id:
        stmt = stmt.where(ExamReport.test_id == test_id)
    if email:
        stmt = stmt.where(ExamReport.email == email)
    stmt = stmt.order_by(ExamReport.generated_at.desc()).offset(skip).limit(limit)
    reports = list(db.execute(stmt).scalars().all())
    logger.debug(
        "Listed %d reports (test_id=%s, email=%s)", len(reports), test_id, email
    )
    return reports


def update_pdf_path(db: Session, report_id: int, pdf_path: str) -> ExamReport | None:
    report = db.get(ExamReport, report_id)
    if report:
        report.pdf_path = pdf_path
        db.commit()
        db.refresh(report)
        logger.info("Report PDF path updated: id=%s, path=%s", report_id, pdf_path)
    else:
        logger.warning("Report not found for PDF path update: id=%s", report_id)
    return report
