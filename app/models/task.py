from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

TASK_TYPE_ASSIGNMENT = "assignment"
TASK_TYPE_QUIZ = "quiz"
TASK_TYPE_LAB = "lab"
TASK_TYPE_PROJECT = "project"
TASK_TYPE_PRESENTATION = "presentation"
TASK_TYPE_EXAM = "exam"
TASK_TYPE_OTHER = "other"

TASK_VISIBILITY_SHARED = "shared"
TASK_VISIBILITY_PERSONAL = "personal"

TASK_PRIORITY_LOW = "low"
TASK_PRIORITY_MEDIUM = "medium"
TASK_PRIORITY_HIGH = "high"
TASK_PRIORITY_URGENT = "urgent"

TASK_STATUS_ACTIVE = "active"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_CANCELLED = "cancelled"
TASK_STATUS_ARCHIVED = "archived"

TASK_PROGRESS_PENDING = "pending"
TASK_PROGRESS_COMPLETED = "completed"


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "task_type IN ('assignment', 'quiz', 'lab', 'project', 'presentation', 'exam', 'other')",
            name="ck_tasks_task_type",
        ),
        CheckConstraint(
            "visibility IN ('shared', 'personal')",
            name="ck_tasks_visibility",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_tasks_priority",
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'cancelled', 'archived')",
            name="ck_tasks_status",
        ),
        CheckConstraint(
            "visibility != 'shared' OR classroom_id IS NOT NULL",
            name="ck_tasks_shared_requires_classroom",
        ),
        CheckConstraint(
            "NOT (visibility = 'shared' AND status = 'completed')",
            name="ck_tasks_shared_not_completed",
        ),
        CheckConstraint(
            "visibility != 'personal' OR status IN ('active', 'completed', 'archived')",
            name="ck_tasks_personal_status",
        ),
        CheckConstraint(
            "class_course_id IS NULL OR classroom_id IS NOT NULL",
            name="ck_tasks_course_requires_classroom",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    classroom_id: Mapped[int | None] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True)
    class_course_id: Mapped[int | None] = mapped_column(ForeignKey("class_courses.id", ondelete="SET NULL"), index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False)
    visibility: Mapped[str] = mapped_column(String(30), nullable=False)
    priority: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    classroom = relationship("Classroom", back_populates="tasks")
    class_course = relationship("ClassCourse", back_populates="tasks")
    creator = relationship("User", back_populates="created_tasks")
    attachments: Mapped[list[TaskAttachment]] = relationship(
        "TaskAttachment",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    progress_records: Mapped[list[TaskProgress]] = relationship(
        "TaskProgress",
        back_populates="task",
        cascade="all, delete-orphan",
    )


class TaskProgress(Base):
    __tablename__ = "task_progress"
    __table_args__ = (
        UniqueConstraint("task_id", "membership_id", name="uq_task_progress_task_membership"),
        CheckConstraint(
            "status IN ('pending', 'completed')",
            name="ck_task_progress_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    membership_id: Mapped[int] = mapped_column(ForeignKey("class_memberships.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=TASK_PROGRESS_PENDING, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    task: Mapped[Task] = relationship("Task", back_populates="progress_records")
    membership = relationship("ClassMembership")


class TaskAttachment(Base):
    __tablename__ = "task_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, index=True, nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped[Task] = relationship("Task", back_populates="attachments")
    uploaded_by = relationship("User")
