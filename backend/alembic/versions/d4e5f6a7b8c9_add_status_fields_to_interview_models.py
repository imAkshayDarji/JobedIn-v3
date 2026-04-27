"""add_status_fields_to_interview_models

Revision ID: d4e5f6a7b8c9
Revises: be0f67fcffd6
Create Date: 2026-04-27 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'be0f67fcffd6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interview_preps', sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='generating'))
    op.add_column('interview_preps', sa.Column('job_description', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('interview_preps', sa.Column('job_title', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('interview_preps', sa.Column('company_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.alter_column('interview_preps', 'job_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.create_index('ix_interview_preps_user_created', 'interview_preps', ['user_id', sa.literal_column('created_at DESC')], unique=False)
    op.drop_constraint('interview_preps_job_id_fkey', 'interview_preps', type_='foreignkey')
    op.create_foreign_key(None, 'interview_preps', 'jobs', ['job_id'], ['id'], ondelete='SET NULL')

    op.add_column('interview_sessions', sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='active'))
    op.add_column('interview_sessions', sa.Column('overall_score', sa.Float(), nullable=True))
    op.add_column('interview_sessions', sa.Column('questions_answered', sa.Integer(), nullable=False, server_default='0'))
    op.create_index('ix_interview_sessions_user_created', 'interview_sessions', ['user_id', sa.literal_column('created_at DESC')], unique=False)


def downgrade() -> None:
    op.drop_index('ix_interview_sessions_user_created', table_name='interview_sessions')
    op.drop_column('interview_sessions', 'questions_answered')
    op.drop_column('interview_sessions', 'overall_score')
    op.drop_column('interview_sessions', 'status')

    op.drop_constraint(None, 'interview_preps', type_='foreignkey')
    op.create_foreign_key('interview_preps_job_id_fkey', 'interview_preps', 'jobs', ['job_id'], ['id'], ondelete='CASCADE')
    op.drop_index('ix_interview_preps_user_created', table_name='interview_preps')
    op.alter_column('interview_preps', 'job_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('interview_preps', 'company_name')
    op.drop_column('interview_preps', 'job_title')
    op.drop_column('interview_preps', 'job_description')
    op.drop_column('interview_preps', 'status')
