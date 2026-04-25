"""add_resume_index_and_status

Revision ID: c3a1f2e4d56b
Revises: b78895d1fb4b
Create Date: 2026-04-25 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3a1f2e4d56b'
down_revision: Union[str, None] = 'b78895d1fb4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('resumes', sa.Column('status', sa.String(), nullable=True))
    op.execute(
        "CREATE INDEX ix_resumes_user_created ON resumes (user_id, created_at DESC)"
    )


def downgrade() -> None:
    op.drop_index('ix_resumes_user_created', table_name='resumes')
    op.drop_column('resumes', 'status')
