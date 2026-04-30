"""Add ATS detection fields to application

Revision ID: e7a8b9c0d1e2
Revises: c3a1f2e4d56b
Create Date: 2026-04-30 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "e7a8b9c0d1e2"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("ats_platform", sa.String(), nullable=True))
    op.add_column("applications", sa.Column("ats_detection_method", sa.String(), nullable=True))
    op.add_column("applications", sa.Column("ats_confidence", sa.Float(), nullable=True))
    op.add_column("applications", sa.Column("ats_form_url", sa.String(), nullable=True))
    op.add_column("applications", sa.Column("ats_detected_fields", JSON(), nullable=True))
    op.add_column("applications", sa.Column("ats_screenshot_path", sa.String(), nullable=True))
    op.add_column("applications", sa.Column("ats_detection_error", sa.String(), nullable=True))
    op.add_column("applications", sa.Column("ats_difficulty", sa.String(), nullable=True))
    op.create_index("ix_applications_user_status", "applications", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_applications_user_status", table_name="applications")
    op.drop_column("applications", "ats_difficulty")
    op.drop_column("applications", "ats_detection_error")
    op.drop_column("applications", "ats_screenshot_path")
    op.drop_column("applications", "ats_detected_fields")
    op.drop_column("applications", "ats_form_url")
    op.drop_column("applications", "ats_confidence")
    op.drop_column("applications", "ats_detection_method")
    op.drop_column("applications", "ats_platform")
