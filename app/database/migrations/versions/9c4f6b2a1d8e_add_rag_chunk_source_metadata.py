"""add rag chunk source metadata

Revision ID: 9c4f6b2a1d8e
Revises: 725bcd6fad8e
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c4f6b2a1d8e"
down_revision: Union[str, Sequence[str], None] = "725bcd6fad8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rag_chunks", sa.Column("source_title", sa.String(length=255), nullable=True))
    op.add_column("rag_chunks", sa.Column("page_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("rag_chunks", "page_number")
    op.drop_column("rag_chunks", "source_title")
