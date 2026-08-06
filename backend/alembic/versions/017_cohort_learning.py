"""Cohort learning part 1 — assessment_attempts, discussion_threads, discussion_posts

Revision ID: 017
Revises: 016
Create Date: 2026-08-06
"""

import sqlalchemy as sa
from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessment_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "item_id",
            sa.String(36),
            sa.ForeignKey("assessment_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "path_id",
            sa.String(36),
            sa.ForeignKey("learning_paths.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("matched_distractor_id", sa.String(36), nullable=True),  # soft ref
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_assessment_attempts_item_id", "assessment_attempts", ["item_id"])
    op.create_index("ix_assessment_attempts_path_id", "assessment_attempts", ["path_id"])
    op.create_index("ix_assessment_attempts_user_id", "assessment_attempts", ["user_id"])

    op.create_table(
        "discussion_threads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "concept_id",
            sa.String(36),
            sa.ForeignKey("path_concepts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("passage_chunk_id", sa.String(36), nullable=True),  # soft ref
        sa.Column("passage_excerpt", sa.Text(), nullable=False, server_default=""),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_discussion_threads_concept_id", "discussion_threads", ["concept_id"])

    op.create_table(
        "discussion_posts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "thread_id",
            sa.String(36),
            sa.ForeignKey("discussion_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_discussion_posts_thread_id", "discussion_posts", ["thread_id"])


def downgrade() -> None:
    op.drop_index("ix_discussion_posts_thread_id", table_name="discussion_posts")
    op.drop_table("discussion_posts")
    op.drop_index("ix_discussion_threads_concept_id", table_name="discussion_threads")
    op.drop_table("discussion_threads")
    op.drop_index("ix_assessment_attempts_user_id", table_name="assessment_attempts")
    op.drop_index("ix_assessment_attempts_path_id", table_name="assessment_attempts")
    op.drop_index("ix_assessment_attempts_item_id", table_name="assessment_attempts")
    op.drop_table("assessment_attempts")
