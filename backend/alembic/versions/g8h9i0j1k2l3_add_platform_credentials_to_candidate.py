"""add platform_credentials JSON to candidate_profiles

Revision ID: g8h9i0j1k2l3
Revises: d5e6f7a8b9c0
Create Date: 2026-06-03 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g8h9i0j1k2l3"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidate_profiles",
        sa.Column("platform_credentials", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidate_profiles", "platform_credentials")
