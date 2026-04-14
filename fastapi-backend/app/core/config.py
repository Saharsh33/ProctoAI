from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = Field(default="MyProctor FastAPI", alias="APP_NAME")
    env: str = Field(default="dev", alias="ENV")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/quizapp",
        alias="DATABASE_URL",
    )

    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    secret_key: str = Field(default="change_me", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(
        default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # ── MinIO / S3 Evidence Storage (Sprint 3) ────────
    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="proctoring-evidence", alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    # ── Logging ───────────────────────────────────────
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str | None = Field(default=None, alias="LOG_FILE")

    def cors_origins_list(self) -> List[str]:
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
