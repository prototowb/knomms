"""Synthesis persistence — syntheses + synthesis_source_projections

Revision ID: 019
Revises: 018
Create Date: 2026-08-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "syntheses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("citations", JSONB(), nullable=False, server_default="[]"),
        sa.Column("source_ids", JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_syntheses_kb_id", "syntheses", ["kb_id"])
    op.create_index("ix_syntheses_user_id", "syntheses", ["user_id"])

    op.create_table(
        "synthesis_source_projections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "synthesis_id",
            sa.String(36),
            sa.ForeignKey("syntheses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.String(36),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("synthesis_id", "kb_id", name="uq_synthesis_projection_kb"),
    )
    op.create_index(
        "ix_synthesis_source_projections_synthesis_id",
        "synthesis_source_projections",
        ["synthesis_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_synthesis_source_projections_synthesis_id",
        table_name="synthesis_source_projections",
    )
    op.drop_table("synthesis_source_projections")
    op.drop_index("ix_syntheses_user_id", table_name="syntheses")
    op.drop_index("ix_syntheses_kb_id", table_name="syntheses")
    op.drop_table("syntheses")
