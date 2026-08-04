"""Asset full-text search — GIN indexes on assets and asset_versions

Revision ID: 007
Revises: 006
Create Date: 2026-06-05
"""

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # GIN index on assets (title + description)
    op.execute(
        "CREATE INDEX ix_assets_fts ON assets "
        "USING gin(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '')))"
    )

    # GIN index on asset_versions (rationale)
    op.execute(
        "CREATE INDEX ix_asset_versions_fts ON asset_versions "
        "USING gin(to_tsvector('english', coalesce(rationale, '')))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_asset_versions_fts")
    op.execute("DROP INDEX IF EXISTS ix_assets_fts")
