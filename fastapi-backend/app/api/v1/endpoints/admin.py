import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func as sa_func, distinct
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.user import User
from app.models.violation import Violation
from app.models.exam import Exam
from app.models.exam_report import ExamReport
from app.crud.admin import (
    create_action,
    list_actions,
    list_violations_with_actions,
    count_violations,
)
from app.schemas.admin import AdminActionCreate, AdminActionOut, AdminViolationOut

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_admin_exam_ids(db: Session, admin_user: User) -> list[str]:
    """Return list of exam ID strings for exams created by this admin."""
    rows = db.query(Exam.examId).filter(Exam.createdBy == admin_user.user_id).all()
    return [str(r[0]) for r in rows]


@router.get("/violations", response_model=list[AdminViolationOut])
def admin_list_violations(
    email: str | None = None,
    test_id: str | None = None,
    violation_type: str | None = None,
    severity: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List violations with their admin action history.
    Only shows violations from exams created by the current admin.
    Supports filters by email, test_id, violation_type, severity.
    Restricted to admin role.
    """
    admin_exam_ids = _get_admin_exam_ids(db, current_user)
    return list_violations_with_actions(
        db,
        email=email,
        test_id=test_id,
        violation_type=violation_type,
        severity=severity,
        skip=skip,
        limit=limit,
        allowed_test_ids=admin_exam_ids,
    )


@router.get("/violations/count")
def admin_count_violations(
    email: str | None = None,
    test_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Return total violation count for dashboard stats (admin's exams only)."""
    admin_exam_ids = _get_admin_exam_ids(db, current_user)
    total = count_violations(db, email=email, test_id=test_id, allowed_test_ids=admin_exam_ids)
    return {"count": total}


@router.post("/actions", response_model=AdminActionOut, status_code=201)
def admin_perform_action(
    payload: AdminActionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Perform an admin action (warn / invalidate / ban) on a violation.
    Records an immutable audit-log entry.
    Only allowed for violations from exams owned by this admin.
    """
    # Validate action_type
    allowed = {"warn", "invalidate", "ban"}
    if payload.action_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"action_type must be one of: {', '.join(sorted(allowed))}",
        )

    # Verify violation exists
    from app.models.violation import Violation
    violation = db.get(Violation, payload.violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    # Verify the violation belongs to one of the admin's exams
    admin_exam_ids = _get_admin_exam_ids(db, current_user)
    if violation.test_id not in admin_exam_ids:
        raise HTTPException(status_code=403, detail="Violation does not belong to your exams")

    return create_action(db, payload, performed_by=current_user.user_id)


@router.get("/actions", response_model=list[AdminActionOut])
def admin_list_actions(
    violation_id: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List admin action audit log. Optionally filter by violation_id."""
    return list_actions(db, violation_id=violation_id, skip=skip, limit=limit, performed_by=current_user.user_id)


@router.get("/exam-students")
def admin_exam_students(
    test_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Return per-exam, per-student summary: email, violation count, trust score.
    Only includes exams created by the current admin.
    If test_id is provided, return students for that exam only (if owned).
    Otherwise return a list of the admin's exams with aggregated student data.
    """
    admin_exam_ids = _get_admin_exam_ids(db, current_user)

    if test_id:
        # Verify this exam belongs to the current admin
        if test_id not in admin_exam_ids:
            raise HTTPException(status_code=403, detail="You do not have permission to access this exam")

        # Per-student breakdown for a specific exam
        rows = (
            db.query(
                Violation.email,
                sa_func.count(Violation.vid).label("violation_count"),
            )
            .filter(Violation.test_id == test_id)
            .group_by(Violation.email)
            .all()
        )

        students = []
        for email, violation_count in rows:
            # Check if report exists
            report = (
                db.query(ExamReport)
                .filter(ExamReport.test_id == test_id, ExamReport.email == email)
                .first()
            )
            students.append({
                "email": email,
                "violation_count": violation_count,
                "trust_score": report.trust_score if report else None,
                "report_id": report.report_id if report else None,
            })

        # Get exam title
        try:
            exam = db.query(Exam).filter(Exam.examId == uuid.UUID(test_id)).first()
            exam_title = exam.title if exam else test_id
        except (ValueError, AttributeError):
            exam_title = test_id

        return {
            "test_id": test_id,
            "exam_title": exam_title,
            "students": students,
        }
    else:
        # Overview: list of admin's exams with student counts and violation counts
        base_q = db.query(
            Violation.test_id,
            sa_func.count(distinct(Violation.email)).label("student_count"),
            sa_func.count(Violation.vid).label("total_violations"),
        )
        # Only include violations from this admin's exams
        if admin_exam_ids:
            base_q = base_q.filter(Violation.test_id.in_(admin_exam_ids))
        else:
            # Admin has no exams, return empty
            return []

        rows = base_q.group_by(Violation.test_id).all()

        result = []
        for test_id, student_count, total_violations in rows:
            try:
                exam = db.query(Exam).filter(Exam.examId == uuid.UUID(test_id)).first()
                exam_title = exam.title if exam else test_id
            except (ValueError, AttributeError):
                exam_title = test_id
            result.append({
                "test_id": test_id,
                "exam_title": exam_title,
                "student_count": student_count,
                "total_violations": total_violations,
            })

        return result
