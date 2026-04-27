"""add_ai_token_usage_table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-27 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_token_usage',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('task', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('model_used', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ai_token_usage_user_id', 'ai_token_usage', ['user_id'], unique=False)
    op.create_index(
        'ix_ai_token_usage_user_created',
        'ai_token_usage',
        ['user_id', sa.literal_column('created_at DESC')],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_ai_token_usage_user_created', table_name='ai_token_usage')
    op.drop_index('ix_ai_token_usage_user_id', table_name='ai_token_usage')
    op.drop_table('ai_token_usage')
