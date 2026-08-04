"""KB sharing — visibility on knowledge_bases

Revision ID: 012
Revises: 011
Create Date: 2026-08-04
"""

import sqlalchemy as sa
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_bases",
        sa.Column("visibility", sa.String(10), nullable=False, server_default="private"),
    )
    op.create_index("ix_knowledge_bases_visibility", "knowledge_bases", ["visibility"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_bases_visibility", table_name="knowledge_bases")
    op.drop_column("knowledge_bases", "visibility")
