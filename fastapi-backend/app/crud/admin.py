import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.admin_action import AdminAction
from app.models.violation import Violation
from app.schemas.admin import AdminActionCreate

logger = logging.getLogger(__name__)


# ── Admin Action CRUD ────────────────────────────────


def create_action(
    db: Session,
    payload: AdminActionCreate,
    performed_by: uuid.UUID,
) -> AdminAction:
    """Record an admin action (warn / invalidate / ban) against a violation."""
    action = AdminAction(
        violation_id=payload.violation_id,
        action_type=payload.action_type,
        reason=payload.reason,
        performed_by=performed_by,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    logger.info(
        "Admin action created: id=%s, type=%s, violation_id=%d, by=%s",
        action.action_id,
        action.action_type,
        payload.violation_id,
        performed_by,
    )
    return action


def list_actions(
    db: Session,
    violation_id: int | None = None,
    performed_by: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AdminAction]:
    """List admin actions with optional filters."""
    stmt = select(AdminAction)
    if violation_id is not None:
        stmt = stmt.where(AdminAction.violation_id == violation_id)
    if performed_by is not None:
        stmt = stmt.where(AdminAction.performed_by == performed_by)
    stmt = stmt.order_by(AdminAction.performed_at.desc()).offset(skip).limit(limit)
    actions = list(db.execute(stmt).scalars().all())
    logger.debug(
        "Listed %d admin actions (violation_id=%s, by=%s)",
        len(actions),
        violation_id,
        performed_by,
    )
    return actions


def list_violations_with_actions(
    db: Session,
    email: str | None = None,
    test_id: str | None = None,
    violation_type: str | None = None,
    severity: str | None = None,
    skip: int = 0,
    limit: int = 100,
    allowed_test_ids: list[str] | None = None,
) -> list[Violation]:
    """List violations with eagerly loaded admin_actions for the admin dashboard.
    When allowed_test_ids is provided, only violations from those exams are returned.
    """
    stmt = select(Violation).options(joinedload(Violation.admin_actions))
    if allowed_test_ids is not None:
        if not allowed_test_ids:
            logger.debug("No allowed test IDs — returning empty violations list")
            return []  # admin has no exams → no violations
        stmt = stmt.where(Violation.test_id.in_(allowed_test_ids))
    if email:
        stmt = stmt.where(Violation.email == email)
    if test_id:
        stmt = stmt.where(Violation.test_id == test_id)
    if violation_type:
        stmt = stmt.where(Violation.violation_type == violation_type)
    if severity:
        stmt = stmt.where(Violation.severity == severity)
    stmt = stmt.order_by(Violation.created_at.desc()).offset(skip).limit(limit)
    # unique() required when using joinedload with collections
    violations = list(db.execute(stmt).unique().scalars().all())
    logger.debug(
        "Listed %d violations with actions (email=%s, test_id=%s, type=%s, severity=%s)",
        len(violations),
        email,
        test_id,
        violation_type,
        severity,
    )
    return violations


def count_violations(
    db: Session,
    email: str | None = None,
    test_id: str | None = None,
    allowed_test_ids: list[str] | None = None,
) -> int:
    """Return total violation count (for dashboard stats).
    When allowed_test_ids is provided, only violations from those exams are counted.
    """
    from sqlalchemy import func

    stmt = select(func.count(Violation.vid))
    if allowed_test_ids is not None:
        if not allowed_test_ids:
            return 0  # admin has no exams → zero violations
        stmt = stmt.where(Violation.test_id.in_(allowed_test_ids))
    if email:
        stmt = stmt.where(Violation.email == email)
    if test_id:
        stmt = stmt.where(Violation.test_id == test_id)
    count = db.execute(stmt).scalar_one()
    logger.debug("Violation count: %d (email=%s, test_id=%s)", count, email, test_id)
    return count
