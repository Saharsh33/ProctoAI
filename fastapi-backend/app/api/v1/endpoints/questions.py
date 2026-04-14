import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app import crud
from app.schemas.question import QuestionCreate, QuestionOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("/", response_model=list[QuestionOut])
def list_questions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info("Listing questions: skip=%d, limit=%d", skip, limit)
    questions = crud.list_questions(db, skip=skip, limit=limit)
    logger.debug("Returned %d questions", len(questions))
    return questions


@router.post("/", response_model=QuestionOut, status_code=201)
def create_question(payload: QuestionCreate, db: Session = Depends(get_db)):
    logger.info("Creating question: exam=%s", payload.examId)
    question = crud.create_question(db, payload)
    logger.info("Question created: qid=%s, exam=%s", question.qid, question.examId)
    return question
