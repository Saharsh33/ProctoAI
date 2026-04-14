from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    exam,
    proctoring,
    reports,
    users,
    window_events,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(exam.router)
api_router.include_router(proctoring.router)
api_router.include_router(window_events.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)
