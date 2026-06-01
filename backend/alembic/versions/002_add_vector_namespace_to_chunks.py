"""add vector_namespace to chunks for single-join KB filtering

Revision ID: 002
Revises: 001
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Stamp each chunk with the KB's vector_namespace so retrieval can filter
    # with a single WHERE clause instead of a 4-hop join through
    # chunks → sources → collection_items → collections → knowledge_bases.
    # Populated at ingest time; NULL for chunks ingested before this migration.
    op.add_column(
        "chunks",
        sa.Column("vector_namespace", sa.String(50), nullable=True),
    )
    op.create_index("ix_chunks_vector_namespace", "chunks", ["vector_namespace"])


def downgrade() -> None:
    op.drop_index("ix_chunks_vector_namespace", table_name="chunks")
    op.drop_column("chunks", "vector_namespace")
