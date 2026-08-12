"""Post editing — discussion_posts.edited_at

Revision ID: 021
Revises: 020
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "discussion_posts",
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("discussion_posts", "edited_at")
