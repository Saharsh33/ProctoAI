from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserSignup, UserLogin, TokenResponse
from app.services.auth_service import signup_user, login_user
from app.core.database import SessionLocal
from app.core.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup")
def signup(data: UserSignup, db: Session = Depends(get_db)):
    user = signup_user(db, data.name, data.email, data.password, data.user_type)
    if not user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return {"message": "User registered successfully"}

@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    token = login_user(db, data.email, data.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": token}

@router.get("/me")
def read_me(current_user: dict = Depends(get_current_user)):
    return current_user