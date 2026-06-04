"""AI Assets Pillar — 7 new tables

Tables: assets, asset_versions, harnesses, harness_assets,
        eval_cases, eval_runs, asset_source_projections

Revision ID: 006
Revises: 005
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── assets ────────────────────────────────────────────────────────────────
    op.create_table(
        "assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("visibility", sa.String(10), nullable=False, server_default="private"),
        sa.Column("fork_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("fork_lineage", ARRAY(sa.String(36)), nullable=False, server_default="{}"),
        sa.Column("forked_from_id", sa.String(36), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_assets_owner_user_id", "assets", ["owner_user_id"])
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])
    op.create_index("ix_assets_visibility", "assets", ["visibility"])

    # ── asset_versions ────────────────────────────────────────────────────────
    op.create_table(
        "asset_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "asset_id",
            sa.String(36),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_num", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("rationale", sa.Text, nullable=False, server_default=""),
        sa.Column("tags", JSONB, nullable=True),
        sa.Column("model_pin", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_asset_versions_asset_id", "asset_versions", ["asset_id"])
    op.create_index("ix_asset_versions_content_hash", "asset_versions", ["content_hash"])
    op.create_unique_constraint(
        "uq_asset_versions_asset_id_version_num", "asset_versions", ["asset_id", "version_num"]
    )

    # ── harnesses ─────────────────────────────────────────────────────────────
    op.create_table(
        "harnesses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("visibility", sa.String(10), nullable=False, server_default="private"),
        sa.Column("fork_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("fork_lineage", ARRAY(sa.String(36)), nullable=False, server_default="{}"),
        sa.Column("forked_from_id", sa.String(36), sa.ForeignKey("harnesses.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_harnesses_owner_user_id", "harnesses", ["owner_user_id"])
    op.create_index("ix_harnesses_visibility", "harnesses", ["visibility"])

    # ── harness_assets ────────────────────────────────────────────────────────
    op.create_table(
        "harness_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "harness_id",
            sa.String(36),
            sa.ForeignKey("harnesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_version_id",
            sa.String(36),
            sa.ForeignKey("asset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_harness_assets_harness_id", "harness_assets", ["harness_id"])
    op.create_index("ix_harness_assets_asset_version_id", "harness_assets", ["asset_version_id"])

    # ── eval_cases ────────────────────────────────────────────────────────────
    op.create_table(
        "eval_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "asset_version_id",
            sa.String(36),
            sa.ForeignKey("asset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("input", sa.Text, nullable=False),
        sa.Column("expected_output", sa.Text, nullable=False),
        sa.Column("grading_strategy", sa.String(20), nullable=False, server_default="exact_match"),
        sa.Column("grading_config", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_eval_cases_asset_version_id", "eval_cases", ["asset_version_id"])

    # ── eval_runs ─────────────────────────────────────────────────────────────
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("harness_id", sa.String(36), sa.ForeignKey("harnesses.id"), nullable=False),
        sa.Column("triggered_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "eval_suite_version_id",
            sa.String(36),
            sa.ForeignKey("asset_versions.id"),
            nullable=True,
        ),
        sa.Column("model_pin", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("metrics", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_eval_runs_harness_id", "eval_runs", ["harness_id"])
    op.create_index("ix_eval_runs_triggered_by", "eval_runs", ["triggered_by"])

    # ── asset_source_projections ──────────────────────────────────────────────
    op.create_table(
        "asset_source_projections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "asset_version_id",
            sa.String(36),
            sa.ForeignKey("asset_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kb_id",
            sa.String(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_asset_source_projections_asset_version_id", "asset_source_projections", ["asset_version_id"])
    op.create_index("ix_asset_source_projections_kb_id", "asset_source_projections", ["kb_id"])
    op.create_unique_constraint(
        "uq_asset_source_projections_version_kb",
        "asset_source_projections",
        ["asset_version_id", "kb_id"],
    )


def downgrade() -> None:
    op.drop_table("asset_source_projections")
    op.drop_table("eval_runs")
    op.drop_table("eval_cases")
    op.drop_table("harness_assets")
    op.drop_table("harnesses")
    op.drop_table("asset_versions")
    op.drop_table("assets")
