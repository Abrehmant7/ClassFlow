"""add search trigram indexes

Revision ID: 3e54c897a21b
Revises: 820286bd906a
Create Date: 2026-09-24
"""

from typing import Sequence, Union

from alembic import op


revision: str = "3e54c897a21b"
down_revision: Union[str, Sequence[str], None] = "820286bd906a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for table, column in (
        ("tasks", "title"),
        ("tasks", "description"),
        ("announcements", "title"),
        ("announcements", "body"),
        ("resources", "title"),
        ("resources", "description"),
    ):
        op.create_index(
            f"ix_{table}_{column}_trgm",
            table,
            [column],
            unique=False,
            postgresql_using="gin",
            postgresql_ops={column: "gin_trgm_ops"},
        )


def downgrade() -> None:
    for table, column in reversed((
        ("tasks", "title"),
        ("tasks", "description"),
        ("announcements", "title"),
        ("announcements", "body"),
        ("resources", "title"),
        ("resources", "description"),
    )):
        op.drop_index(f"ix_{table}_{column}_trgm", table_name=table)
