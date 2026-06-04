"""add resume pdf and s3 fields

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-06-04 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "h9i0j1k2l3m4"
down_revision: Union[str, None] = "g8h9i0j1k2l3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("pdf_s3_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("resumes", sa.Column("pdf_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column(
        "resumes",
        sa.Column("uploaded_resume_s3_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column("cover_letters", sa.Column("pdf_s3_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("cover_letters", sa.Column("pdf_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column(
        "candidate_profiles",
        sa.Column("resume_s3_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("resume_upload_filename", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("resume_uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidate_profiles", "resume_uploaded_at")
    op.drop_column("candidate_profiles", "resume_upload_filename")
    op.drop_column("candidate_profiles", "resume_s3_key")
    op.drop_column("cover_letters", "pdf_url")
    op.drop_column("cover_letters", "pdf_s3_key")
    op.drop_column("resumes", "uploaded_resume_s3_key")
    op.drop_column("resumes", "pdf_url")
    op.drop_column("resumes", "pdf_s3_key")
