from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ClassFlow"
    ENVIRONMENT: str = "local"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/classflow"

    SECRET_KEY: str = "change-me-in-local-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    FRONTEND_PASSWORD_RESET_URL: str = "http://localhost:5173/reset-password"

    CORS_ORIGINS: list[str] = Field(default_factory=list)

    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    VECTOR_STORE_PROVIDER: str = "pgvector"

    TASK_ATTACHMENT_STORAGE_DIR: str = "storage/task_attachments"
    TASK_ATTACHMENT_MAX_SIZE_BYTES: int = 10 * 1024 * 1024
    TASK_ATTACHMENT_ALLOWED_EXTENSIONS: list[str] = Field(
        default_factory=lambda: ["pdf", "docx", "pptx", "xlsx", "txt", "png", "jpg", "jpeg", "zip"]
    )
    TASK_ATTACHMENT_ALLOWED_CONTENT_TYPES: list[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/plain",
            "image/png",
            "image/jpeg",
            "application/zip",
            "application/x-zip-compressed",
        ]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CLASSFLOW_",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
