"""Learner progress — concept_progress table

Revision ID: 010
Revises: 009
Create Date: 2026-08-04
"""

import sqlalchemy as sa
from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "concept_progress",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "concept_id",
            sa.String(36),
            sa.ForeignKey("path_concepts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("learned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "concept_id", name="uq_concept_progress_user_concept"),
    )


def downgrade() -> None:
    op.drop_table("concept_progress")
