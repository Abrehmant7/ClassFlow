"""create tasks progress and attachments

Revision ID: f2659f4668ac
Revises: 00f7fc38ba77
Create Date: 2026-08-13 18:50:16.022668

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2659f4668ac'
down_revision: Union[str, Sequence[str], None] = "00f7fc38ba77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("classroom_id", sa.Integer(), nullable=False),
        sa.Column("class_course_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("task_type", sa.String(length=30), nullable=False),
        sa.Column("visibility", sa.String(length=30), nullable=False),
        sa.Column("priority", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "task_type IN ('assignment', 'quiz', 'lab', 'project', 'presentation', 'exam', 'other')",
            name="ck_tasks_task_type",
        ),
        sa.CheckConstraint("visibility IN ('shared', 'private')", name="ck_tasks_visibility"),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", name="ck_tasks_priority"),
        sa.CheckConstraint("status IN ('active', 'completed', 'cancelled', 'archived')", name="ck_tasks_status"),
        sa.ForeignKeyConstraint(["class_course_id"], ["class_courses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_id"), "tasks", ["id"], unique=False)
    op.create_index(op.f("ix_tasks_classroom_id"), "tasks", ["classroom_id"], unique=False)
    op.create_index(op.f("ix_tasks_class_course_id"), "tasks", ["class_course_id"], unique=False)
    op.create_index(op.f("ix_tasks_created_by_user_id"), "tasks", ["created_by_user_id"], unique=False)

    op.create_table(
        "task_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'completed')", name="ck_task_progress_status"),
        sa.ForeignKeyConstraint(["membership_id"], ["class_memberships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "membership_id", name="uq_task_progress_task_membership"),
    )
    op.create_index(op.f("ix_task_progress_id"), "task_progress", ["id"], unique=False)
    op.create_index(op.f("ix_task_progress_task_id"), "task_progress", ["task_id"], unique=False)
    op.create_index(op.f("ix_task_progress_membership_id"), "task_progress", ["membership_id"], unique=False)

    op.create_table(
        "task_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_attachments_id"), "task_attachments", ["id"], unique=False)
    op.create_index(op.f("ix_task_attachments_task_id"), "task_attachments", ["task_id"], unique=False)
    op.create_index(op.f("ix_task_attachments_uploaded_by_user_id"), "task_attachments", ["uploaded_by_user_id"], unique=False)
    op.create_index(op.f("ix_task_attachments_storage_key"), "task_attachments", ["storage_key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_task_attachments_storage_key"), table_name="task_attachments")
    op.drop_index(op.f("ix_task_attachments_uploaded_by_user_id"), table_name="task_attachments")
    op.drop_index(op.f("ix_task_attachments_task_id"), table_name="task_attachments")
    op.drop_index(op.f("ix_task_attachments_id"), table_name="task_attachments")
    op.drop_table("task_attachments")

    op.drop_index(op.f("ix_task_progress_membership_id"), table_name="task_progress")
    op.drop_index(op.f("ix_task_progress_task_id"), table_name="task_progress")
    op.drop_index(op.f("ix_task_progress_id"), table_name="task_progress")
    op.drop_table("task_progress")

    op.drop_index(op.f("ix_tasks_created_by_user_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_class_course_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_classroom_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_id"), table_name="tasks")
    op.drop_table("tasks")