import logging
import uuid
from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.schemas.exam import ExamCreate, ExamUpdate

logger = logging.getLogger(__name__)


def create(
    db: Session, exam_in: ExamCreate, created_by: "uuid.UUID | None" = None
) -> Exam:
    exam = Exam(
        title=exam_in.title,
        duration=exam_in.duration,
        startTime=exam_in.startTime,
        rules=exam_in.rules,
        status=exam_in.status,
        createdBy=created_by,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    logger.info(
        "Exam created: id=%s, title='%s', created_by=%s",
        exam.examId,
        exam.title,
        created_by,
    )
    return exam


def list_exams(
    db: Session, skip: int = 0, limit: int = 100, created_by: "uuid.UUID | None" = None
) -> list[Exam]:
    """List exams with pagination. Optionally filter by creator."""
    q = db.query(Exam)
    if created_by is not None:
        q = q.filter(Exam.createdBy == created_by)
    exams = q.offset(skip).limit(limit).all()
    logger.debug(
        "Listed %d exams (skip=%d, limit=%d, created_by=%s)",
        len(exams),
        skip,
        limit,
        created_by,
    )
    return exams


def get_by_id(db: Session, exam_id: uuid.UUID) -> Exam | None:
    """Get a single exam by its ID."""
    exam = db.query(Exam).filter(Exam.examId == exam_id).first()
    if exam:
        logger.debug("Exam found: id=%s", exam_id)
    else:
        logger.debug("Exam not found: id=%s", exam_id)
    return exam


def update(db: Session, exam_id: uuid.UUID, exam_in: ExamUpdate) -> Exam | None:
    """Update an exam by its ID."""
    exam = get_by_id(db, exam_id)
    if not exam:
        return None

    update_data = exam_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(exam, field, value)

    db.commit()
    db.refresh(exam)
    logger.info("Exam updated: id=%s, fields=%s", exam_id, list(update_data.keys()))
    return exam


def delete(db: Session, exam_id: uuid.UUID) -> bool:
    """Delete an exam by its ID."""
    exam = get_by_id(db, exam_id)
    if not exam:
        return False

    db.delete(exam)
    db.commit()
    logger.info("Exam deleted: id=%s", exam_id)
    return True
