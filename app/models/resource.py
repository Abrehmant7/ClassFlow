from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database.base import Base

RAG_SOURCE_TASK = "task"
RAG_SOURCE_TASK_ATTACHMENT = "task_attachment"
RAG_SOURCE_RESOURCE = "resource"
RAG_SOURCE_COURSE = "course"
RAG_SOURCE_ANNOUNCEMENT = "announcement"

RESOURCE_INDEX_PENDING = "pending"
RESOURCE_INDEX_PROCESSING = "processing"
RESOURCE_INDEX_INDEXED = "indexed"
RESOURCE_INDEX_FAILED = "failed"


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint(
            "indexing_status IN ('pending', 'processing', 'indexed', 'failed')",
            name="ck_resources_indexing_status",
        ),
        CheckConstraint("file_size >= 0", name="ck_resources_file_size"),
        Index(
            "ix_resources_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index(
            "ix_resources_description_trgm",
            "description",
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True)
    class_course_id: Mapped[int | None] = mapped_column(ForeignKey("class_courses.id", ondelete="CASCADE"), index=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    content_type: Mapped[str] = mapped_column(String(100))
    # Historical records may lack metadata; every new upload supplies both values.
    file_size: Mapped[int | None] = mapped_column(Integer)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    indexing_status: Mapped[str] = mapped_column(String(30), default=RESOURCE_INDEX_PENDING, server_default=RESOURCE_INDEX_PENDING, index=True)
    indexing_error: Mapped[str | None] = mapped_column(Text)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True)
    class_course_id: Mapped[int | None] = mapped_column(ForeignKey("class_courses.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(30), index=True)
    source_id: Mapped[int] = mapped_column(Integer, index=True)
    source_title: Mapped[str | None] = mapped_column(String(255))
    page_number: Mapped[int | None] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(768))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
