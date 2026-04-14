import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.storage import ensure_bucket
from app.db.init_db import init_db
from app.services.violation_logger import violation_buffer

# ── Initialize logging before anything else ──
setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    init_db()
    logger.info("Database initialized")

    try:
        ensure_bucket()
        logger.info("MinIO bucket ready")
    except Exception as exc:
        logger.warning(
            "MinIO bucket init skipped (service may be unavailable): %s", exc
        )

    violation_buffer.start()
    logger.info("ViolationBuffer background task started")

    yield

    # ── Shutdown ──
    await violation_buffer.stop()
    logger.info("ViolationBuffer stopped")


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    origins = settings.cors_origins_list()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
