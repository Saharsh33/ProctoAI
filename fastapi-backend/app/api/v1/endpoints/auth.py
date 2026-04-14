import logging

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_role
from app import crud
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    """Register a new user. Returns the created user object."""
    logger.info("Signup attempt for email=%s, role=%s", payload.email, payload.role)
    if crud.get_user_by_email(db, str(payload.email)):
        logger.warning("Signup rejected — email already registered: %s", payload.email)
        raise HTTPException(status_code=409, detail="Email already registered")
    user = crud.create_user(db, payload)
    logger.info("User created: id=%s, email=%s, role=%s", user.user_id, user.email, user.role.value)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return a JWT access token."""
    logger.info("Login attempt for email=%s", payload.email)
    user = crud.authenticate_user(db, str(payload.email), payload.password)
    if not user:
        logger.warning("Login failed — invalid credentials for email=%s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
    logger.info("Login successful: user_id=%s, role=%s", user.user_id, user.role.value)
    return TokenResponse(access_token=token)


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def token(
    username: str = Body(...), 
    password: str = Body(...), 
    db: Session = Depends(get_db)
):
    """Token endpoint (username = email)."""
    logger.info("Token request for username=%s", username)
    user = crud.authenticate_user(db, username, password)
    if not user:
        logger.warning("Token request failed — invalid credentials for username=%s", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token({"sub": str(user.user_id), "role": user.role.value})
    logger.info("Token issued: user_id=%s", user.user_id)
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    logger.debug("GET /me — user_id=%s", current_user.user_id)
    return current_user


@router.get("/admin-only", response_model=UserOut)
def admin_only(current_user: User = Depends(require_role("admin"))):
    """Example endpoint restricted to users with the 'admin' role."""
    logger.debug("GET /admin-only — user_id=%s", current_user.user_id)
    return current_user


@router.get("/student-only", response_model=UserOut)
def student_only(current_user: User = Depends(require_role("student"))):
    """Example endpoint restricted to users with the 'student' role."""
    logger.debug("GET /student-only — user_id=%s", current_user.user_id)
    return current_user
