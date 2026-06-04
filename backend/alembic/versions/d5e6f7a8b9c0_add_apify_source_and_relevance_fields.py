"""Add apify source and relevance fields

Revision ID: d5e6f7a8b9c0
Revises: a3b4c5d6e7f8
Create Date: 2026-05-31 16:00:00.000000

Adds 'apify' value to jobsource enum, plus relevance_score and
relevance_reason columns to the jobs table for AI-scored job filtering.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE jobsource ADD VALUE 'apify'")
    op.add_column("jobs", sa.Column("relevance_score", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("relevance_reason", sa.Text(), nullable=True))
    op.create_index(
        "ix_jobs_source_relevance",
        "jobs",
        ["source", "relevance_score"],
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_source_relevance", table_name="jobs")
    op.drop_column("jobs", "relevance_reason")
    op.drop_column("jobs", "relevance_score")
    op.execute("ALTER TYPE jobsource RENAME TO jobsource_old")
    op.execute(
        "CREATE TYPE jobsource AS ENUM "
        "('linkedin', 'adzuna', 'jsearch', 'remotive', 'reed')"
    )
    op.execute(
        "ALTER TABLE jobs ALTER COLUMN source TYPE jobsource "
        "USING source::text::jobsource"
    )
    op.execute("DROP TYPE jobsource_old")
