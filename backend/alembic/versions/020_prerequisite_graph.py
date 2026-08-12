"""Prerequisite graph — path_concepts.prerequisites

Revision ID: 020
Revises: 019
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "path_concepts",
        sa.Column("prerequisites", JSONB(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("path_concepts", "prerequisites")
