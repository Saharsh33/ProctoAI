import logging
import uuid
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)

security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Validate Bearer JWT and return the corresponding User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token.credentials)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            logger.warning("JWT payload missing 'sub' claim")
            raise credentials_exception
    except JWTError as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise credentials_exception

    from app import crud  # local import to avoid circular dependency

    user = crud.get_user_by_id(db, uuid.UUID(user_id_str))
    if user is None:
        logger.warning("JWT valid but user not found: sub=%s", user_id_str)
        raise credentials_exception
    logger.debug("Authenticated user: id=%s, role=%s", user.user_id, user.role.value)
    return user


def require_role(*roles: str):
    """Dependency factory that restricts access to users with given roles."""

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in roles:
            logger.warning(
                "Access denied: user=%s (role=%s) tried to access endpoint requiring %s",
                current_user.user_id,
                current_user.role.value,
                roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your role",
            )
        return current_user

    return _check


require_admin = require_role("admin")
require_student = require_role("student")
