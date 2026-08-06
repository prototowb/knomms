"""Harness study KBs — harnesses.study_kb_id + harness_study_docs

Revision ID: 016
Revises: 015
Create Date: 2026-08-06
"""

import sqlalchemy as sa
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "harnesses",
        sa.Column(
            "study_kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_table(
        "harness_study_docs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "harness_id",
            sa.String(36),
            sa.ForeignKey("harnesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("doc_kind", sa.String(20), nullable=False),  # slot | eval_suite | eval_run
        sa.Column("ref_id", sa.String(36), nullable=False),  # asset_version_id | eval_run_id
        sa.Column("source_id", sa.String(36), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("kb_id", "doc_kind", "ref_id", name="uq_harness_study_docs_kb_kind_ref"),
    )
    op.create_index("ix_harness_study_docs_harness_id", "harness_study_docs", ["harness_id"])


def downgrade() -> None:
    op.drop_index("ix_harness_study_docs_harness_id", table_name="harness_study_docs")
    op.drop_table("harness_study_docs")
    op.drop_column("harnesses", "study_kb_id")
