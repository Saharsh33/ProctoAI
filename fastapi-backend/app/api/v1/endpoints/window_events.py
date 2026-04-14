import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app import crud
from app.schemas.window_events import WindowEventCreate, WindowEventOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/window-events", tags=["window-events"])


@router.get("/", response_model=list[WindowEventOut])
def list_events(
    email: str | None = None,
    test_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    logger.info("Listing window events: email=%s, test_id=%s, skip=%d, limit=%d", email, test_id, skip, limit)
    events = crud.list_events(db, email=email, test_id=test_id, skip=skip, limit=limit)
    logger.debug("Returned %d window events", len(events))
    return events


@router.post("/", response_model=WindowEventOut, status_code=201)
def create_event(payload: WindowEventCreate, db: Session = Depends(get_db)):
    logger.info("Creating window event: email=%s, test_id=%s", payload.email, payload.test_id)
    event = crud.create_window_event(db, payload)
    logger.debug("Window event created: id=%s", event.wid)
    return event
