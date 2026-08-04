"""KB keyword search — GIN FTS index on chunks.text

Revision ID: 011
Revises: 010
Create Date: 2026-08-04
"""

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Plain CREATE INDEX is fine at self-hosted scale; on a large deployment
    # run CREATE INDEX CONCURRENTLY manually instead (cannot run inside
    # alembic's transaction).
    op.execute(
        "CREATE INDEX ix_chunks_fts ON chunks "
        "USING gin(to_tsvector('english', text))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_chunks_fts")
