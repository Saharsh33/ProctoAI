from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    exam,
    proctoring,
    window_events,
    reports,
    admin,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(exam.router)
api_router.include_router(proctoring.router)
api_router.include_router(window_events.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)
