"""Eval run provider — eval_runs.provider column for the cloud eval adapter

Revision ID: 015
Revises: 014
Create Date: 2026-08-06
"""

import sqlalchemy as sa
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default backfills every existing run as local (OQ-22)
    op.add_column(
        "eval_runs",
        sa.Column("provider", sa.String(20), nullable=False, server_default="ollama"),
    )


def downgrade() -> None:
    op.drop_column("eval_runs", "provider")
