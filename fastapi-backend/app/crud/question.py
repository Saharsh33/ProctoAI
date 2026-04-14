import logging
import uuid

from app.models.question import Question
from app.schemas.question import QuestionCreate, QuestionUpdate
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_by_id(db: Session, questions_uid: int) -> Question | None:
    question = db.get(Question, questions_uid)
    logger.debug(
        "Question lookup: qid=%s, found=%s", questions_uid, question is not None
    )
    return question


def list_questions(db: Session, skip: int = 0, limit: int = 100) -> list[Question]:
    stmt = select(Question).offset(skip).limit(limit)
    questions = list(db.execute(stmt).scalars().all())
    logger.debug("Listed %d questions (skip=%d, limit=%d)", len(questions), skip, limit)
    return questions


def list_questions_by_exam(
    db: Session, exam_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[Question]:
    """List all questions for a specific exam."""
    stmt = select(Question).where(Question.examId == exam_id).offset(skip).limit(limit)
    questions = list(db.execute(stmt).scalars().all())
    logger.debug("Listed %d questions for exam %s", len(questions), exam_id)
    return questions


def create(db: Session, q_in: QuestionCreate) -> Question:
    question = Question(**q_in.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    logger.info("Question created: qid=%s, exam=%s", question.qid, question.examId)
    return question


def update(db: Session, questions_uid: int, q_in: QuestionUpdate) -> Question | None:
    """Update a question by its ID."""
    question = get_by_id(db, questions_uid)
    if not question:
        return None

    update_data = q_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    db.commit()
    db.refresh(question)
    logger.info(
        "Question updated: qid=%s, fields=%s", questions_uid, list(update_data.keys())
    )
    return question


def delete(db: Session, questions_uid: int) -> bool:
    """Delete a question by its ID."""
    question = get_by_id(db, questions_uid)
    if not question:
        return False

    db.delete(question)
    db.commit()
    logger.info("Question deleted: qid=%s", questions_uid)
    return True
