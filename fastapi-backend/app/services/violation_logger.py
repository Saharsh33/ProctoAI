"""
Violation Logger Service (Sprint 3 – REQ-9, REQ-10).

Provides:
  • Async batch-write buffer that flushes every 2 seconds
  • 3× exponential-backoff retry on DB write failure
  • Violation-type classification / validation
  • Target < 500 ms per DB write (achieved via batching)
  • Background task integration with FastAPI lifespan
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from enum import Enum

from app.db.session import SessionLocal
from app.models.violation import Violation
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Violation type classification enum ─────────────────
VALID_VIOLATION_TYPES = {
    "face_absent",
    "multiple_faces",
    "tab_switch",
    "audio_violation",
    "identity_mismatch",
}

SEVERITY_MAP = {
    "face_absent": "warning",
    "multiple_faces": "critical",
    "tab_switch": "warning",
    "audio_violation": "warning",
    "identity_mismatch": "critical",
}


def classify_violation(violation_type: str) -> dict:
    """Return normalised type and severity.  Unknown types default to 'warning'."""
    vtype = violation_type.strip().lower()
    if vtype not in VALID_VIOLATION_TYPES:
        logger.warning("Unknown violation type '%s', defaulting to warning", vtype)
    return {
        "violation_type": vtype,
        "severity": SEVERITY_MAP.get(vtype, "warning"),
    }


# ── Retry helper (3× exponential back-off) ────────────
MAX_RETRIES = 3
BASE_DELAY_S = 0.1  # 100 ms → 200 ms → 400 ms


async def _write_batch_with_retry(batch: list[dict]) -> bool:
    """
    Write a list of violation dicts to the DB with retry.
    Returns True on success, False if all retries exhausted.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        db: Session | None = None
        t0 = time.monotonic()
        try:
            db = SessionLocal()
            objects = [Violation(**item) for item in batch]
            db.add_all(objects)
            db.commit()
            elapsed_ms = (time.monotonic() - t0) * 1000
            logger.info(
                "Batch write OK: %d violations in %.1f ms (attempt %d)",
                len(batch),
                elapsed_ms,
                attempt,
            )
            return True
        except Exception as exc:
            if db:
                db.rollback()
            delay = BASE_DELAY_S * (2 ** (attempt - 1))
            logger.warning(
                "Batch write failed (attempt %d/%d): %s – retrying in %.1fs",
                attempt,
                MAX_RETRIES,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
        finally:
            if db:
                db.close()
    logger.error(
        "Batch write FAILED after %d retries – %d violations lost",
        MAX_RETRIES,
        len(batch),
    )
    return False


# ── Async batch buffer ─────────────────────────────────
FLUSH_INTERVAL_S = 2.0  # flush every 2 seconds


class ViolationBuffer:
    """
    Thread-safe async buffer that accumulates violations and flushes them
    to PostgreSQL in batches every FLUSH_INTERVAL_S seconds.
    """

    def __init__(self, flush_interval: float = FLUSH_INTERVAL_S):
        self._buffer: deque[dict] = deque()
        self._flush_interval = flush_interval
        self._task: asyncio.Task | None = None
        self._running = False

    def enqueue(self, violation_dict: dict) -> None:
        """Add a violation to the buffer (called from endpoint handler)."""
        # Classify / normalise before buffering
        classification = classify_violation(violation_dict.get("violation_type", ""))
        violation_dict["violation_type"] = classification["violation_type"]
        # Only override severity if not explicitly set to something more severe
        if violation_dict.get("severity") not in ("critical",):
            violation_dict["severity"] = classification["severity"]
        self._buffer.append(violation_dict)

    async def _flush(self) -> int:
        """Drain the buffer and write to DB.  Returns number of items flushed."""
        if not self._buffer:
            return 0
        batch = []
        while self._buffer:
            batch.append(self._buffer.popleft())
        await _write_batch_with_retry(batch)
        return len(batch)

    async def _run_loop(self) -> None:
        """Background loop that flushes the buffer on a fixed interval."""
        self._running = True
        logger.info("ViolationBuffer started (flush every %.1fs)", self._flush_interval)
        while self._running:
            await asyncio.sleep(self._flush_interval)
            try:
                n = await self._flush()
                if n:
                    logger.debug("Flushed %d violations", n)
            except Exception as exc:
                logger.error("ViolationBuffer flush error: %s", exc)

    def start(self) -> None:
        """Start the background flush loop (call in FastAPI lifespan)."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the background loop and flush remaining items."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Final flush
        await self._flush()
        logger.info("ViolationBuffer stopped, final flush complete")

    @property
    def pending_count(self) -> int:
        return len(self._buffer)


# ── Module-level singleton ─────────────────────────────
violation_buffer = ViolationBuffer()
