"""
MinIO / S3-compatible object storage service (Sprint 3 – REQ-9).

Provides:
  • Bucket auto-creation on startup
  • Presigned PUT URL generation for direct client uploads (bypass server bandwidth)
  • Presigned GET URL generation for evidence retrieval
  • Object key builder with structured paths: evidence/{test_id}/{email}/{timestamp}_{type}.png
"""

from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import urlencode

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Singleton MinIO client ─────────────────────────────
_client: Minio | None = None


def get_minio_client() -> Minio:
    """Return a reusable MinIO client singleton."""
    global _client
    if _client is None:
        _client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def ensure_bucket() -> None:
    """Create the evidence bucket if it doesn't exist.  Call once at app startup."""
    client = get_minio_client()
    bucket = settings.minio_bucket
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info("Created MinIO bucket: %s", bucket)
        else:
            logger.info("MinIO bucket already exists: %s", bucket)
    except S3Error as exc:
        logger.warning("MinIO bucket check failed (non-fatal): %s", exc)


def build_object_key(
    test_id: str,
    email: str,
    violation_type: str,
    timestamp_ms: int,
    ext: str = "png",
) -> str:
    """Build a deterministic, human-readable object key."""
    safe_email = email.replace("@", "_at_").replace(".", "_")
    return f"evidence/{test_id}/{safe_email}/{timestamp_ms}_{violation_type}.{ext}"


def generate_presigned_put_url(
    object_key: str,
    content_type: str = "image/png",
    expires: timedelta = timedelta(minutes=10),
) -> str:
    """Generate a presigned PUT URL so the browser can upload directly to MinIO."""
    client = get_minio_client()
    url = client.get_presigned_url(
        "PUT",
        settings.minio_bucket,
        object_key,
        expires=expires,
    )
    return url


def generate_presigned_get_url(
    object_key: str,
    expires: timedelta = timedelta(hours=1),
) -> str:
    """Generate a presigned GET URL for viewing stored evidence."""
    client = get_minio_client()
    return client.get_presigned_url(
        "GET",
        settings.minio_bucket,
        object_key,
        expires=expires,
    )


def get_public_object_url(object_key: str) -> str:
    """Build the permanent object URL (for storage in DB — not presigned)."""
    scheme = "https" if settings.minio_secure else "http"
    return f"{scheme}://{settings.minio_endpoint}/{settings.minio_bucket}/{object_key}"
