import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.proctoring_log import ProctoringLog
from app.schemas.proctoring import ProctoringLogCreate

logger = logging.getLogger(__name__)


def create(db: Session, log_in: ProctoringLogCreate) -> ProctoringLog:
    log = ProctoringLog(**log_in.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    logger.info(
        "Proctoring log created: id=%s, email=%s, test_id=%s",
        log.lid,
        log.email,
        log.test_id,
    )
    return log


def list_logs(
    db: Session,
    email: str | None = None,
    test_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[ProctoringLog]:
    stmt = select(ProctoringLog)
    if email:
        stmt = stmt.where(ProctoringLog.email == email)
    if test_id:
        stmt = stmt.where(ProctoringLog.test_id == test_id)
    stmt = stmt.order_by(ProctoringLog.log_time.desc()).offset(skip).limit(limit)
    logs = list(db.execute(stmt).scalars().all())
    logger.debug(
        "Listed %d proctoring logs (email=%s, test_id=%s)", len(logs), email, test_id
    )
    return logs
