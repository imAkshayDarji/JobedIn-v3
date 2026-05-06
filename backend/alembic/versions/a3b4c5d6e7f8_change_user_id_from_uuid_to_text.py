"""Change user_id columns from UUID to TEXT for Clerk migration

Clerk user IDs are strings (user_xxx format), not UUIDs.
This migration converts all user_id columns from UUID to TEXT.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-05-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("candidate_profiles", "user_id",
                    existing_type=sa.Uuid(),
                    type_=sa.Text(),
                    existing_nullable=False)

    op.alter_column("applications", "user_id",
                    existing_type=sa.Uuid(),
                    type_=sa.Text(),
                    existing_nullable=False)

    op.alter_column("cover_letters", "user_id",
                    existing_type=sa.Uuid(),
                    type_=sa.Text(),
                    existing_nullable=False)

    op.alter_column("interview_preps", "user_id",
                    existing_type=sa.Uuid(),
                    type_=sa.Text(),
                    existing_nullable=False)

    op.alter_column("resumes", "user_id",
                    existing_type=sa.Uuid(),
                    type_=sa.Text(),
                    existing_nullable=False)

    op.alter_column("interview_sessions", "user_id",
                    existing_type=sa.Uuid(),
                    type_=sa.Text(),
                    existing_nullable=False)

    op.alter_column("job_matches", "user_id",
                    existing_type=sa.Uuid(),
                    type_=sa.Text(),
                    existing_nullable=False)

    op.alter_column("ai_token_usage", "user_id",
                    existing_type=sa.Uuid(),
                    type_=sa.Text(),
                    existing_nullable=False)


def downgrade() -> None:
    op.alter_column("ai_token_usage", "user_id",
                    existing_type=sa.Text(),
                    type_=sa.Uuid(),
                    existing_nullable=False)

    op.alter_column("job_matches", "user_id",
                    existing_type=sa.Text(),
                    type_=sa.Uuid(),
                    existing_nullable=False)

    op.alter_column("interview_sessions", "user_id",
                    existing_type=sa.Text(),
                    type_=sa.Uuid(),
                    existing_nullable=False)

    op.alter_column("resumes", "user_id",
                    existing_type=sa.Text(),
                    type_=sa.Uuid(),
                    existing_nullable=False)

    op.alter_column("interview_preps", "user_id",
                    existing_type=sa.Text(),
                    type_=sa.Uuid(),
                    existing_nullable=False)

    op.alter_column("cover_letters", "user_id",
                    existing_type=sa.Text(),
                    type_=sa.Uuid(),
                    existing_nullable=False)

    op.alter_column("applications", "user_id",
                    existing_type=sa.Text(),
                    type_=sa.Uuid(),
                    existing_nullable=False)

    op.alter_column("candidate_profiles", "user_id",
                    existing_type=sa.Text(),
                    type_=sa.Uuid(),
                    existing_nullable=False)
