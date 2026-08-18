"""make personal tasks classroom optional

Revision ID: b7428b2d4f91
Revises: f2659f4668ac
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b7428b2d4f91"
down_revision: Union[str, Sequence[str], None] = "f2659f4668ac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_tasks_visibility", "tasks", type_="check")

    op.alter_column("tasks", "classroom_id", nullable=True)
    op.execute("UPDATE tasks SET visibility = 'personal' WHERE visibility = 'private'")

    op.create_check_constraint(
        "ck_tasks_visibility",
        "tasks",
        "visibility IN ('shared', 'personal')",
    )
    op.create_check_constraint(
        "ck_tasks_shared_requires_classroom",
        "tasks",
        "visibility != 'shared' OR classroom_id IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_tasks_shared_not_completed",
        "tasks",
        "NOT (visibility = 'shared' AND status = 'completed')",
    )
    op.create_check_constraint(
        "ck_tasks_personal_status",
        "tasks",
        "visibility != 'personal' OR status IN ('active', 'completed', 'archived')",
    )
    op.create_check_constraint(
        "ck_tasks_course_requires_classroom",
        "tasks",
        "class_course_id IS NULL OR classroom_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tasks_course_requires_classroom", "tasks", type_="check")
    op.drop_constraint("ck_tasks_personal_status", "tasks", type_="check")
    op.drop_constraint("ck_tasks_shared_not_completed", "tasks", type_="check")
    op.drop_constraint("ck_tasks_shared_requires_classroom", "tasks", type_="check")
    op.drop_constraint("ck_tasks_visibility", "tasks", type_="check")

    op.execute("UPDATE tasks SET visibility = 'private' WHERE visibility = 'personal'")
    op.alter_column("tasks", "classroom_id", nullable=False)

    op.create_check_constraint(
        "ck_tasks_visibility",
        "tasks",
        "visibility IN ('shared', 'private')",
    )
