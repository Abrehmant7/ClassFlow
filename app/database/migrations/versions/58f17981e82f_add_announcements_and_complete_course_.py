"""add announcements and complete course resources

Revision ID: 58f17981e82f
Revises: 9c4f6b2a1d8e
Create Date: 2026-09-22 22:59:49.816611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58f17981e82f'
down_revision: Union[str, Sequence[str], None] = '9c4f6b2a1d8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Reviewed autogeneration: rename legacy resource columns without losing data.
    op.create_table('announcements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('classroom_id', sa.Integer(), nullable=False),
    sa.Column('class_course_id', sa.Integer(), nullable=True),
    sa.Column('created_by_user_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('is_pinned', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['class_course_id'], ['class_courses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['classroom_id'], ['classrooms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_announcements_class_course_id'), 'announcements', ['class_course_id'], unique=False)
    op.create_index(op.f('ix_announcements_classroom_id'), 'announcements', ['classroom_id'], unique=False)
    op.create_index(op.f('ix_announcements_created_by_user_id'), 'announcements', ['created_by_user_id'], unique=False)
    op.create_index(op.f('ix_announcements_id'), 'announcements', ['id'], unique=False)
    op.drop_constraint(op.f('rag_chunks_class_course_id_fkey'), 'rag_chunks', type_='foreignkey')
    op.create_foreign_key('rag_chunks_class_course_id_fkey', 'rag_chunks', 'class_courses', ['class_course_id'], ['id'], ondelete='CASCADE')
    op.add_column('resources', sa.Column('description', sa.Text(), nullable=True))
    op.alter_column('resources', 'file_path', new_column_name='storage_key', existing_type=sa.String(500), existing_nullable=False)
    op.alter_column('resources', 'file_type', new_column_name='content_type', existing_type=sa.String(30), type_=sa.String(100), existing_nullable=False)
    op.execute("UPDATE resources SET content_type = 'application/pdf' WHERE lower(content_type) = 'pdf'")
    # File metadata cannot be safely reconstructed by a portable DB migration.
    # Leave historical metadata unknown; new uploads always supply size/checksum.
    op.add_column('resources', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('resources', sa.Column('checksum_sha256', sa.String(length=64), nullable=True))
    op.add_column('resources', sa.Column('indexing_status', sa.String(length=30), server_default='pending', nullable=False))
    op.add_column('resources', sa.Column('indexing_error', sa.Text(), nullable=True))
    op.add_column('resources', sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('resources', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.execute('UPDATE resources SET updated_at = created_at')
    op.create_check_constraint('ck_resources_indexing_status', 'resources', "indexing_status IN ('pending', 'processing', 'indexed', 'failed')")
    op.create_check_constraint('ck_resources_file_size', 'resources', 'file_size >= 0')
    op.create_index(op.f('ix_resources_indexing_status'), 'resources', ['indexing_status'], unique=False)
    op.create_index(op.f('ix_resources_storage_key'), 'resources', ['storage_key'], unique=True)
    op.drop_constraint(op.f('resources_class_course_id_fkey'), 'resources', type_='foreignkey')
    op.create_foreign_key('resources_class_course_id_fkey', 'resources', 'class_courses', ['class_course_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('resources_class_course_id_fkey', 'resources', type_='foreignkey')
    op.create_foreign_key(op.f('resources_class_course_id_fkey'), 'resources', 'class_courses', ['class_course_id'], ['id'], ondelete='SET NULL')
    op.drop_index(op.f('ix_resources_storage_key'), table_name='resources')
    op.drop_index(op.f('ix_resources_indexing_status'), table_name='resources')
    op.drop_constraint('ck_resources_indexing_status', 'resources', type_='check')
    op.drop_constraint('ck_resources_file_size', 'resources', type_='check')
    op.drop_column('resources', 'updated_at')
    op.drop_column('resources', 'indexed_at')
    op.drop_column('resources', 'indexing_error')
    op.drop_column('resources', 'indexing_status')
    op.drop_column('resources', 'checksum_sha256')
    op.drop_column('resources', 'file_size')
    op.execute("UPDATE resources SET content_type = 'pdf' WHERE content_type = 'application/pdf'")
    op.alter_column('resources', 'content_type', new_column_name='file_type', existing_type=sa.String(100), type_=sa.String(30), existing_nullable=False)
    op.alter_column('resources', 'storage_key', new_column_name='file_path', existing_type=sa.String(500), existing_nullable=False)
    op.drop_column('resources', 'description')
    op.drop_constraint('rag_chunks_class_course_id_fkey', 'rag_chunks', type_='foreignkey')
    op.create_foreign_key(op.f('rag_chunks_class_course_id_fkey'), 'rag_chunks', 'class_courses', ['class_course_id'], ['id'], ondelete='SET NULL')
    op.drop_index(op.f('ix_announcements_id'), table_name='announcements')
    op.drop_index(op.f('ix_announcements_created_by_user_id'), table_name='announcements')
    op.drop_index(op.f('ix_announcements_classroom_id'), table_name='announcements')
    op.drop_index(op.f('ix_announcements_class_course_id'), table_name='announcements')
    op.drop_table('announcements')
