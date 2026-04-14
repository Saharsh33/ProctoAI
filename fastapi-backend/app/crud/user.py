import logging
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    user = db.get(User, user_id)
    if user:
        logger.debug("User found by id: %s", user_id)
    else:
        logger.debug("User not found by id: %s", user_id)
    return user


def get_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    user = db.execute(stmt).scalars().first()
    if user:
        logger.debug("User found by email: %s", email)
    else:
        logger.debug("User not found by email: %s", email)
    return user


def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    stmt = select(User).offset(skip).limit(limit)
    users = list(db.execute(stmt).scalars().all())
    logger.debug("Listed %d users (skip=%d, limit=%d)", len(users), skip, limit)
    return users


def create(db: Session, user_in: UserCreate) -> User:
    user = User(
        name=user_in.name,
        email=str(user_in.email),
        password_hash=hash_password(user_in.password),
        role=user_in.role,
        user_image=user_in.user_image,
        user_login=user_in.user_login,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(
        "Created user: id=%s, email=%s, role=%s",
        user.user_id,
        user.email,
        user.role.value,
    )
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Return the user if credentials are valid, else None."""
    user = get_by_email(db, email)
    if user is None:
        logger.debug("Auth failed — email not found: %s", email)
        return None
    if not verify_password(password, user.password_hash):
        logger.debug("Auth failed — wrong password for: %s", email)
        return None
    logger.debug("Auth successful for: %s", email)
    return user


def update(db: Session, user: User, user_in: UserUpdate) -> User:
    data = user_in.model_dump(exclude_unset=True)
    if "password" in data:
        data["password_hash"] = hash_password(data.pop("password"))
    for k, v in data.items():
        setattr(user, k, v)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Updated user: id=%s, fields=%s", user.user_id, list(data.keys()))
    return user
