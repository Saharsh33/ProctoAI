import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.violation import Violation
from app.schemas.proctoring import ViolationCreate

logger = logging.getLogger(__name__)


def create(db: Session, payload: ViolationCreate) -> Violation:
    violation = Violation(**payload.model_dump())
    db.add(violation)
    db.commit()
    db.refresh(violation)
    logger.info(
        "Violation created: id=%s, email=%s, test_id=%s, type=%s",
        violation.vid,
        violation.email,
        violation.test_id,
        violation.violation_type,
    )
    return violation


def list_violations(
    db: Session,
    email: str | None = None,
    test_id: str | None = None,
    violation_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Violation]:
    stmt = select(Violation)
    if email:
        stmt = stmt.where(Violation.email == email)
    if test_id:
        stmt = stmt.where(Violation.test_id == test_id)
    if violation_type:
        stmt = stmt.where(Violation.violation_type == violation_type)
    stmt = stmt.order_by(Violation.created_at.desc()).offset(skip).limit(limit)
    violations = list(db.execute(stmt).scalars().all())
    logger.debug(
        "Listed %d violations (email=%s, test_id=%s, type=%s)",
        len(violations),
        email,
        test_id,
        violation_type,
    )
    return violations
