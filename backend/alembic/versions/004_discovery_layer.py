"""discovery layer — extend collections + collection_items for boards

Adds:
  collections.layout_config  JSONB   — swim-lane / canvas config
  collections.ai_summary     TEXT    — AI-generated board summary
  collections.board_embedding vector(768) — centroid for semantic recommendations
  collections.fork_count     INTEGER — denormalized for trending sort
  collection_items.lane      VARCHAR(100) — swim-lane label

Revision ID: 004
Revises: 003
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── collections ───────────────────────────────────────────────────────────
    op.add_column("collections", sa.Column("layout_config", JSONB, nullable=True))
    op.add_column("collections", sa.Column("ai_summary", sa.Text, nullable=True))
    # board_embedding: use placeholder text then ALTER to vector(768), mirroring
    # the chunks.embedding pattern from migration 001.
    op.add_column("collections", sa.Column("board_embedding", sa.Text, nullable=True))
    op.execute("ALTER TABLE collections ALTER COLUMN board_embedding TYPE vector(768) USING NULL")
    op.add_column("collections", sa.Column("fork_count", sa.Integer, nullable=False, server_default="0"))

    # HNSW index for board-level nearest-neighbor search.
    # Use a plain index here (same dev caveat as chunks — run CONCURRENTLY in prod).
    op.execute(
        "CREATE INDEX ix_collections_board_embedding_hnsw "
        "ON collections USING hnsw (board_embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64) "
        "WHERE board_embedding IS NOT NULL"
    )
    op.create_index("ix_collections_fork_count", "collections", ["fork_count"])
    op.create_index("ix_collections_visibility", "collections", ["visibility"])

    # ── collection_items ──────────────────────────────────────────────────────
    op.add_column(
        "collection_items",
        sa.Column("lane", sa.String(100), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("collection_items", "lane")
    op.drop_index("ix_collections_visibility", table_name="collections")
    op.drop_index("ix_collections_fork_count", table_name="collections")
    op.execute("DROP INDEX IF EXISTS ix_collections_board_embedding_hnsw")
    op.drop_column("collections", "fork_count")
    op.drop_column("collections", "board_embedding")
    op.drop_column("collections", "ai_summary")
    op.drop_column("collections", "layout_config")
