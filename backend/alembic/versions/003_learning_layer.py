"""learning layer — LearningPath, PathConcept, AssessmentItem, Distractor tables

Revision ID: 003
Revises: 002
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_paths",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("learning_goal", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("time_budget_hours", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_learning_paths_kb_id", "learning_paths", ["kb_id"])
    op.create_index("ix_learning_paths_user_id", "learning_paths", ["user_id"])

    op.create_table(
        "path_concepts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "path_id",
            sa.String(36),
            sa.ForeignKey("learning_paths.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("explanation_text", sa.Text, nullable=False),
        sa.Column(
            "explanation_passage_ids",
            JSONB,
            nullable=False,
            server_default="'[]'::jsonb",
        ),
        sa.Column(
            "source_passages",
            JSONB,
            nullable=False,
            server_default="'[]'::jsonb",
        ),
        sa.Column("instructor_annotation", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_path_concepts_path_id", "path_concepts", ["path_id"])

    op.create_table(
        "assessment_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "concept_id",
            sa.String(36),
            sa.ForeignKey("path_concepts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("grounding_passage_id", sa.String(36), nullable=False),
        sa.Column("correct_answer", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_assessment_items_concept_id", "assessment_items", ["concept_id"])

    op.create_table(
        "distractors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "item_id",
            sa.String(36),
            sa.ForeignKey("assessment_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("why_wrong_passage_id", sa.String(36), nullable=False),
        sa.Column("misconception_label", sa.Text, nullable=True),
    )
    op.create_index("ix_distractors_item_id", "distractors", ["item_id"])


def downgrade() -> None:
    op.drop_table("distractors")
    op.drop_table("assessment_items")
    op.drop_table("path_concepts")
    op.drop_table("learning_paths")
