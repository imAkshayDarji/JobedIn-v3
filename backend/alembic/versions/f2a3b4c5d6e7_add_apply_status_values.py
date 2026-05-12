"""Add new ApplicationStatus values for auto-apply

Revision ID: f2a3b4c5d6e7
Revises: e7a8b9c0d1e2
Create Date: 2026-05-01 14:00:00.000000

No schema change. The ApplicationStatus enum values are stored as VARCHAR
in PostgreSQL. This migration documents the new valid values:
  - applying
  - applied_with_issues
  - manual_required
  - failed
"""
from alembic import op
import sqlalchemy as sa


revision = "f2a3b4c5d6e7"
down_revision = "e7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE applicationstatus ADD VALUE IF NOT EXISTS 'applying'"
    )
    op.execute(
        "ALTER TYPE applicationstatus ADD VALUE IF NOT EXISTS 'applied_with_issues'"
    )
    op.execute(
        "ALTER TYPE applicationstatus ADD VALUE IF NOT EXISTS 'manual_required'"
    )
    op.execute(
        "ALTER TYPE applicationstatus ADD VALUE IF NOT EXISTS 'failed'"
    )


def downgrade() -> None:
    pass
