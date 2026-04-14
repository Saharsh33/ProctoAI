import logging
import uuid
from datetime import datetime, timezone

from app import crud
from app.api.deps import get_current_user, get_db, require_role
from app.models.exam import Exam
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamOut, ExamUpdate
from app.schemas.exam_submission import ExamSubmission, ExamSubmissionResponse
from app.schemas.question import QuestionCreate, QuestionOut, QuestionUpdate
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exam", tags=["exam"])


def _check_admin_owns_exam(exam: Exam, admin: User) -> None:
    """Raise 403 if the admin did not create this exam."""
    if exam.createdBy != admin.user_id:
        logger.warning(
            "Access denied: admin %s tried to access exam %s owned by %s",
            admin.user_id,
            exam.examId,
            exam.createdBy,
        )
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this exam",
        )


@router.post("/create", response_model=ExamOut, status_code=201)
def create_exam(
    payload: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Create a new exam. Restricted to admin role only."""
    logger.info(
        "Creating exam: title='%s', admin=%s", payload.title, current_user.user_id
    )
    exam = crud.create_exam(db, payload, created_by=current_user.user_id)
    logger.info("Exam created: id=%s, title='%s'", exam.examId, exam.title)
    return exam


@router.get("/list", response_model=list[ExamOut])
def list_exams(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List exams. Admin sees only their own exams; students see all."""
    logger.info(
        "Listing exams: role=%s, user=%s, skip=%d, limit=%d",
        current_user.role.value,
        current_user.user_id,
        skip,
        limit,
    )
    if current_user.role.value == "admin":
        exams = crud.list_exams(
            db, skip=skip, limit=limit, created_by=current_user.user_id
        )
    else:
        exams = crud.list_exams(db, skip=skip, limit=limit)
    logger.debug("Returned %d exams", len(exams))
    return exams


@router.get("/my-submissions", response_model=list[str])
def my_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Return list of exam IDs that the current student has already submitted."""
    logger.info("Fetching submissions for student=%s", current_user.user_id)
    from app.models.student import Student

    rows = (
        db.query(Student.examId)
        .filter(Student.uid == current_user.user_id)
        .distinct()
        .all()
    )
    result = [str(r[0]) for r in rows]
    logger.debug("Student %s has %d submissions", current_user.user_id, len(result))
    return result


@router.get("/{exam_id}", response_model=ExamOut)
def get_exam(
    exam_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single exam by ID. Admin can only see their own exams."""
    logger.info("Fetching exam: id=%s, user=%s", exam_id, current_user.user_id)
    exam = crud.get_exam_by_id(db, exam_id)
    if not exam:
        logger.warning("Exam not found: id=%s", exam_id)
        raise HTTPException(status_code=404, detail="Exam not found")
    # Admin can only access exams they created
    if current_user.role.value == "admin":
        _check_admin_owns_exam(exam, current_user)
    return exam


@router.get("/{exam_id}/questions", response_model=list[QuestionOut])
def list_exam_questions(
    exam_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all questions for a specific exam. Admin can only see their own exams."""
    logger.info("Listing questions: exam=%s, user=%s", exam_id, current_user.user_id)
    exam = crud.get_exam_by_id(db, exam_id)
    if not exam:
        logger.warning("Exam not found for question listing: id=%s", exam_id)
        raise HTTPException(status_code=404, detail="Exam not found")
    if current_user.role.value == "admin":
        _check_admin_owns_exam(exam, current_user)
    questions = crud.list_questions_by_exam(db, exam_id, skip=skip, limit=limit)
    logger.debug("Returned %d questions for exam %s", len(questions), exam_id)
    return questions


@router.post("/{exam_id}/questions", response_model=QuestionOut, status_code=201)
def add_question_to_exam(
    exam_id: uuid.UUID,
    payload: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Add a question to an exam. Admin can only add to their own exams."""
    logger.info("Adding question to exam=%s by admin=%s", exam_id, current_user.user_id)
    exam = crud.get_exam_by_id(db, exam_id)
    if not exam:
        logger.warning("Exam not found for adding question: id=%s", exam_id)
        raise HTTPException(status_code=404, detail="Exam not found")
    _check_admin_owns_exam(exam, current_user)

    payload.examId = exam_id
    payload.uid = current_user.user_id
    question = crud.create_question(db, payload)
    logger.info("Question added: qid=%s to exam=%s", question.qid, exam_id)
    return question


@router.post("/{exam_id}/submit", response_model=ExamSubmissionResponse)
def submit_exam(
    exam_id: uuid.UUID,
    payload: ExamSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Submit exam answers. Restricted to student role only."""
    logger.info("Exam submission: exam=%s, student=%s", exam_id, current_user.user_id)
    exam = crud.get_exam_by_id(db, exam_id)
    if not exam:
        logger.warning("Exam not found for submission: id=%s", exam_id)
        raise HTTPException(status_code=404, detail="Exam not found")

    if payload.examId != exam_id:
        logger.warning("Exam ID mismatch: payload=%s, url=%s", payload.examId, exam_id)
        raise HTTPException(status_code=400, detail="Exam ID mismatch")

    existing_answers = crud.get_student_answers(db, current_user.user_id, exam_id)
    if existing_answers:
        logger.warning(
            "Duplicate submission rejected: student=%s, exam=%s",
            current_user.user_id,
            exam_id,
        )
        raise HTTPException(
            status_code=409, detail="You have already submitted this exam"
        )

    submitted_count = 0
    for answer in payload.answers:
        crud.create_answer(
            db=db,
            uid=current_user.user_id,
            exam_id=exam_id,
            test_id=str(exam_id),
            qid=answer.qid,
            answer=answer.answer,
            email=current_user.email,
        )
        submitted_count += 1

    logger.info(
        "Exam submitted: exam=%s, student=%s, answers=%d",
        exam_id,
        current_user.user_id,
        submitted_count,
    )
    return ExamSubmissionResponse(
        message="Exam submitted successfully",
        submitted_count=submitted_count,
        server_confirmed_at=datetime.now(timezone.utc),
    )


@router.put("/{exam_id}", response_model=ExamOut)
def update_exam(
    exam_id: uuid.UUID,
    payload: ExamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Update an exam. Admin can only update their own exams."""
    logger.info("Updating exam: id=%s, admin=%s", exam_id, current_user.user_id)
    exam = crud.get_exam_by_id(db, exam_id)
    if not exam:
        logger.warning("Exam not found for update: id=%s", exam_id)
        raise HTTPException(status_code=404, detail="Exam not found")
    _check_admin_owns_exam(exam, current_user)

    updated = crud.update_exam(db, exam_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Exam not found")
    logger.info("Exam updated: id=%s", exam_id)
    return updated


@router.delete("/{exam_id}", status_code=204)
def delete_exam(
    exam_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Delete an exam. Admin can only delete their own exams."""
    logger.info("Deleting exam: id=%s, admin=%s", exam_id, current_user.user_id)
    exam = crud.get_exam_by_id(db, exam_id)
    if not exam:
        logger.warning("Exam not found for deletion: id=%s", exam_id)
        raise HTTPException(status_code=404, detail="Exam not found")
    _check_admin_owns_exam(exam, current_user)

    success = crud.delete_exam(db, exam_id)
    if not success:
        raise HTTPException(status_code=404, detail="Exam not found")
    logger.info("Exam deleted: id=%s", exam_id)
    return None


@router.put("/{exam_id}/questions/{question_id}", response_model=QuestionOut)
def update_question(
    exam_id: uuid.UUID,
    question_id: int,
    payload: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Update a question in an exam. Admin can only modify their own exams."""
    logger.info(
        "Updating question: qid=%d, exam=%s, admin=%s",
        question_id,
        exam_id,
        current_user.user_id,
    )
    exam = crud.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    _check_admin_owns_exam(exam, current_user)

    question = crud.update_question(db, question_id, payload)
    if not question:
        logger.warning("Question not found for update: qid=%d", question_id)
        raise HTTPException(status_code=404, detail="Question not found")

    if question.examId != exam_id:
        logger.warning("Question %d does not belong to exam %s", question_id, exam_id)
        raise HTTPException(
            status_code=400, detail="Question does not belong to this exam"
        )

    logger.info("Question updated: qid=%d, exam=%s", question_id, exam_id)
    return question


@router.delete("/{exam_id}/questions/{question_id}", status_code=204)
def delete_question(
    exam_id: uuid.UUID,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Delete a question from an exam. Admin can only modify their own exams."""
    logger.info(
        "Deleting question: qid=%d, exam=%s, admin=%s",
        question_id,
        exam_id,
        current_user.user_id,
    )
    exam = crud.get_exam_by_id(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    _check_admin_owns_exam(exam, current_user)

    question = crud.get_question_by_id(db, question_id)
    if not question:
        logger.warning("Question not found for deletion: qid=%d", question_id)
        raise HTTPException(status_code=404, detail="Question not found")

    if question.examId != exam_id:
        logger.warning("Question %d does not belong to exam %s", question_id, exam_id)
        raise HTTPException(
            status_code=400, detail="Question does not belong to this exam"
        )

    success = crud.delete_question(db, question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Question not found")

    logger.info("Question deleted: qid=%d, exam=%s", question_id, exam_id)
    return None
