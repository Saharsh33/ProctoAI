import logging
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.teacher import Teacher
from app.schemas.teacher import TeacherCreate

logger = logging.getLogger(__name__)


def get_by_id(db: Session, tid: int) -> Teacher | None:
    teacher = db.get(Teacher, tid)
    logger.debug("Teacher lookup: tid=%s, found=%s", tid, teacher is not None)
    return teacher


def list_teachers(db: Session, skip: int = 0, limit: int = 100) -> list[Teacher]:
    stmt = select(Teacher).offset(skip).limit(limit)
    teachers = list(db.execute(stmt).scalars().all())
    logger.debug("Listed %d teachers (skip=%d, limit=%d)", len(teachers), skip, limit)
    return teachers


def create(db: Session, teacher_in: TeacherCreate) -> Teacher:
    teacher = Teacher(**teacher_in.model_dump(exclude_none=True))
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    logger.info("Teacher created: tid=%s", teacher.tid)
    return teacher
