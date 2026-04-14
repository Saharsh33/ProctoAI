import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app import crud
from app.schemas.user import UserCreate, UserOut, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserOut])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    logger.info(
        "Listing users: skip=%d, limit=%d, requested_by=%s",
        skip,
        limit,
        current_user.user_id,
    )
    users = crud.list_users(db, skip=skip, limit=limit)
    logger.debug("Returned %d users", len(users))
    return users


@router.get("/{uid}", response_model=UserOut)
def get_user(
    uid: int,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    logger.info("Fetching user: uid=%s, requested_by=%s", uid, current_user.user_id)
    user = crud.get_user_by_id(db, uid)
    if not user:
        logger.warning("User not found: uid=%s", uid)
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    logger.info(
        "Creating user: email=%s, role=%s, requested_by=%s",
        payload.email,
        payload.role,
        current_user.user_id,
    )
    existing = crud.get_user_by_email(db, str(payload.email))
    if existing:
        logger.warning(
            "User creation rejected — email already exists: %s", payload.email
        )
        raise HTTPException(status_code=409, detail="Email already exists")
    user = crud.create_user(db, payload)
    logger.info("User created via /users endpoint: id=%s", user.user_id)
    return user


@router.patch("/{uid}", response_model=UserOut)
def update_user(
    uid: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user),
):
    logger.info("Updating user: uid=%s, requested_by=%s", uid, current_user.user_id)
    user = crud.get_user_by_id(db, uid)
    if not user:
        logger.warning("User not found for update: uid=%s", uid)
        raise HTTPException(status_code=404, detail="User not found")
    updated = crud.update_user(db, user, payload)
    logger.info("User updated: uid=%s", uid)
    return updated
