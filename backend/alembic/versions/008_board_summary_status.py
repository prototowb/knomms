"""Async board summary — summary_status on collections

Revision ID: 008
Revises: 007
Create Date: 2026-08-04
"""

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "collections",
        sa.Column("summary_status", sa.String(20), nullable=False, server_default="idle"),
    )


def downgrade() -> None:
    op.drop_column("collections", "summary_status")
