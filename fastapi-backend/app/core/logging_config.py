"""
Centralized logging configuration for ProctoAI backend.

Call `setup_logging()` once at app startup (before any other imports
that create loggers) to apply a consistent format, level, and optional
file output to every logger in the `app.*` namespace.
"""

import logging
import sys
from pathlib import Path

from app.core.config import settings


def setup_logging() -> None:
    """Configure root and app-level loggers with a uniform format."""

    level_name = getattr(settings, "log_level", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
    )
    datefmt = "%Y-%m-%d %H:%M:%S"

    # ── Console handler (always) ──────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    # ── File handler (optional) ───────────────────────
    log_file = getattr(settings, "log_file", None)
    file_handler = None
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    # ── Apply to root logger ─────────────────────────
    root = logging.getLogger()
    root.setLevel(level)
    # Clear any pre-existing handlers to avoid duplicate output
    root.handlers.clear()
    root.addHandler(console_handler)
    if file_handler:
        root.addHandler(file_handler)

    # Quiet noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("app").info(
        "Logging configured: level=%s, file=%s", level_name, log_file or "none"
    )
