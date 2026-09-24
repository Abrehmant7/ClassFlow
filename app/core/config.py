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
    GEMINI_GENERATION_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    VECTOR_STORE_PROVIDER: str = "pgvector"
    RAG_EMBEDDING_DIMENSIONS: int = 768
    RAG_EMBEDDING_BATCH_SIZE: int = 20
    RAG_TOP_K: int = 5
    RAG_MAX_DISTANCE: float = 0.8
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 150
    RAG_MAX_OUTPUT_TOKENS: int = 800
    RAG_MAX_DOCUMENT_PAGES: int = 200
    RAG_MAX_EXTRACTED_CHARACTERS: int = 500_000
    RAG_CHAT_FILE_MAX_SIZE_BYTES: int = 5 * 1024 * 1024
    RAG_CHAT_FILE_MAX_PAGES: int = 100
    RAG_CHAT_FILE_MAX_EXTRACTED_CHARACTERS: int = 200_000
    RAG_CHAT_FILE_MAX_CHUNKS: int = 200

    COURSE_RESOURCE_STORAGE_DIR: str = "storage/course_resources"
    COURSE_RESOURCE_MAX_SIZE_BYTES: int = Field(default=10 * 1024 * 1024, gt=0)
    COURSE_RESOURCE_ALLOWED_EXTENSIONS: list[str] = Field(default_factory=lambda: ["pdf"])
    COURSE_RESOURCE_ALLOWED_CONTENT_TYPES: list[str] = Field(default_factory=lambda: ["application/pdf"])

    REMINDER_LEAD_MINUTES: int = Field(default=24 * 60, ge=0)
    REMINDER_BATCH_SIZE: int = Field(default=100, gt=0)
    DASHBOARD_LIST_LIMIT: int = Field(default=5, gt=0)

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
