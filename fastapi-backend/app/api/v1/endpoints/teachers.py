import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app import crud
from app.schemas.teacher import TeacherCreate, TeacherOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("/", response_model=list[TeacherOut])
def list_teachers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logger.info("Listing teachers: skip=%d, limit=%d", skip, limit)
    teachers = crud.list_teachers(db, skip=skip, limit=limit)
    logger.debug("Returned %d teachers", len(teachers))
    return teachers


@router.get("/{tid}", response_model=TeacherOut)
def get_teacher(tid: int, db: Session = Depends(get_db)):
    logger.info("Fetching teacher: tid=%d", tid)
    teacher = crud.get_teacher_by_id(db, tid)
    if not teacher:
        logger.warning("Teacher not found: tid=%d", tid)
        raise HTTPException(status_code=404, detail="Teacher/test not found")
    return teacher


@router.post("/", response_model=TeacherOut, status_code=201)
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db)):
    logger.info("Creating teacher record")
    teacher = crud.create_teacher(db, payload)
    logger.info("Teacher created: tid=%s", teacher.tid)
    return teacher
