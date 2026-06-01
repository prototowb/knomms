"""add kb_id to sources for clean source-to-KB attribution

Revision ID: 005
Revises: 004
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column(
            "kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_sources_kb_id", "sources", ["kb_id"])


def downgrade() -> None:
    op.drop_index("ix_sources_kb_id", table_name="sources")
    op.drop_column("sources", "kb_id")
