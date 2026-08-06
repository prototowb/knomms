"""Mastery gates — learning_paths.mastery_mode + mastery_threshold

Revision ID: 018
Revises: 017
Create Date: 2026-08-06
"""

import sqlalchemy as sa
from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_paths",
        sa.Column("mastery_mode", sa.String(10), nullable=False, server_default="off"),
    )
    op.add_column(
        "learning_paths",
        sa.Column("mastery_threshold", sa.Float(), nullable=False, server_default="0.8"),
    )


def downgrade() -> None:
    op.drop_column("learning_paths", "mastery_threshold")
    op.drop_column("learning_paths", "mastery_mode")
