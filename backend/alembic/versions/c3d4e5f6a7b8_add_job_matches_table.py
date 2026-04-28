"""Add job_matches table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-28 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("skills_score", sa.Float(), nullable=False),
        sa.Column("experience_score", sa.Float(), nullable=False),
        sa.Column("role_relevance_score", sa.Float(), nullable=False),
        sa.Column("location_score", sa.Float(), nullable=False),
        sa.Column("matched_skills", sa.JSON(), nullable=True),
        sa.Column("missing_skills", sa.JSON(), nullable=True),
        sa.Column("scored_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_job_matches_user_id", "job_matches", ["user_id"])
    op.create_unique_constraint("uq_job_matches_user_job", "job_matches", ["user_id", "job_id"])
    op.create_index("ix_job_matches_user_score", "job_matches", ["user_id", "match_score"])


def downgrade() -> None:
    op.drop_index("ix_job_matches_user_score", table_name="job_matches")
    op.drop_constraint("uq_job_matches_user_job", "job_matches", type_="unique")
    op.drop_index("ix_job_matches_user_id", table_name="job_matches")
    op.drop_table("job_matches")
