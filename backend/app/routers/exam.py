from fastapi import APIRouter, Depends

from app.core.auth import require_admin, require_student

router = APIRouter(prefix="/exam", tags=["Exam"])


@router.post("/create")
def create_exam(current_user: dict = Depends(require_admin)):
    return {"message": "Exam created", "created_by": current_user["email"]}


@router.get("/list")
def list_exams(current_user: dict = Depends(require_student)):
    return {"message": "Exam list", "student": current_user["email"]}