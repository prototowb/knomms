"""baseline schema — pgvector extension + 5 core tables

Revision ID: 001
Revises:
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pgvector extension ────────────────────────────────────────────────────
    # MUST come before creating the chunks table with a vector column.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("handle", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_handle", "users", ["handle"], unique=True)

    # ── sources ───────────────────────────────────────────────────────────────
    op.create_table(
        "sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("raw_url", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("visibility", sa.String(10), nullable=False, server_default="private"),
        sa.Column("ingestion_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("ingestion_job_id", sa.String(36), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_sources_owner_user_id", "sources", ["owner_user_id"])
    op.create_index("ix_sources_content_hash", "sources", ["content_hash"])

    # ── chunks ────────────────────────────────────────────────────────────────
    op.create_table(
        "chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "source_id",
            sa.String(36),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("locator", sa.String(128), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        # vector(768) — requires pgvector extension (created above)
        sa.Column("embedding", sa.Text(), nullable=True),   # placeholder; altered below
        sa.Column("embedding_model_id", sa.String(64), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("is_overlap", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # Replace the placeholder text column with the real vector type
    op.execute("ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(768) USING NULL")

    op.create_index("ix_chunks_source_id", "chunks", ["source_id"])
    op.create_index("ix_chunks_content_hash", "chunks", ["content_hash"])
    op.create_index("ix_chunks_source_seq", "chunks", ["source_id", "seq"])
    op.create_index("ix_chunks_hash_source", "chunks", ["content_hash", "source_id"])

    # HNSW index — use CONCURRENTLY to avoid locking the table.
    # Note: CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
    # Alembic wraps migrations in transactions by default; this is handled via
    # op.get_bind().execution_options(no_autoflush=True) — but CONCURRENTLY
    # requires being outside a transaction. In production, run this index
    # creation separately after the migration completes:
    #   CREATE INDEX CONCURRENTLY ix_chunks_embedding_hnsw
    #   ON chunks USING hnsw (embedding vector_cosine_ops)
    #   WITH (m = 16, ef_construction = 64);
    #
    # For development (small data volume), a regular index is fine:
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw "
        "ON chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )

    # ── knowledge_bases ───────────────────────────────────────────────────────
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("vector_namespace", sa.String(50), nullable=False),
        sa.Column(
            "embedding_model_id",
            sa.String(64),
            nullable=False,
            server_default="nomic-embed-text-v1.5",
        ),
        sa.Column("index_status", sa.String(20), nullable=False, server_default="building"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_knowledge_bases_owner", "knowledge_bases", ["owner_user_id"])
    op.create_index(
        "ix_knowledge_bases_namespace", "knowledge_bases", ["vector_namespace"], unique=True
    )

    # ── collections ───────────────────────────────────────────────────────────
    op.create_table(
        "collections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("visibility", sa.String(10), nullable=False, server_default="private"),
        sa.Column(
            "forked_from_id",
            sa.String(36),
            sa.ForeignKey("collections.id"),
            nullable=True,
        ),
        sa.Column(
            "fork_lineage",
            postgresql.ARRAY(sa.String(36)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_collections_owner", "collections", ["owner_user_id"])

    # ── collection_items ──────────────────────────────────────────────────────
    op.create_table(
        "collection_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "collection_id",
            sa.String(36),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.String(36),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("added_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_collection_items_collection_id", "collection_items", ["collection_id"])

    # ── knowledge_base_collection (join table) ────────────────────────────────
    op.create_table(
        "knowledge_base_collection",
        sa.Column("kb_id", sa.String(36), sa.ForeignKey("knowledge_bases.id"), primary_key=True),
        sa.Column(
            "collection_id",
            sa.String(36),
            sa.ForeignKey("collections.id"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("knowledge_base_collection")
    op.drop_table("collection_items")
    op.drop_table("collections")
    op.drop_table("knowledge_bases")
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("sources")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
