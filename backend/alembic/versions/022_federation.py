"""Federation part 2 — federation_feeds + federation_subscriptions

Revision ID: 022
Revises: 021
Create Date: 2026-08-20
"""

import sqlalchemy as sa
from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "federation_feeds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_federation_feeds_slug", "federation_feeds", ["slug"])

    op.create_table(
        "federation_subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("feed_url", sa.Text(), nullable=False),
        sa.Column("bundle_hash", sa.String(64), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("federation_subscriptions")
    op.drop_index("ix_federation_feeds_slug", table_name="federation_feeds")
    op.drop_table("federation_feeds")
