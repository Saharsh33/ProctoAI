import logging
import uuid

from app.models.student import Student
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def create_answer(
    db: Session,
    uid: uuid.UUID,
    exam_id: uuid.UUID,
    test_id: str,
    qid: str,
    answer: str,
    email: str,
) -> Student:
    """Create or update a student answer."""
    # Check if answer already exists for this student, exam, and question
    existing = (
        db.query(Student)
        .filter(Student.uid == uid, Student.examId == exam_id, Student.qid == qid)
        .first()
    )

    if existing:
        # Update existing answer
        logger.debug(
            "Updating existing answer: uid=%s, exam=%s, qid=%s", uid, exam_id, qid
        )
        existing.ans = answer
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new answer
        logger.debug("Creating new answer: uid=%s, exam=%s, qid=%s", uid, exam_id, qid)
        answer_record = Student(
            uid=uid, email=email, test_id=test_id, examId=exam_id, qid=qid, ans=answer
        )
        db.add(answer_record)
        db.commit()
        db.refresh(answer_record)
        return answer_record


def get_student_answers(
    db: Session, uid: uuid.UUID, exam_id: uuid.UUID
) -> list[Student]:
    """Get all answers submitted by a student for a specific exam."""
    answers = (
        db.query(Student).filter(Student.uid == uid, Student.examId == exam_id).all()
    )
    logger.debug("Retrieved %d answers: uid=%s, exam=%s", len(answers), uid, exam_id)
    return answers
