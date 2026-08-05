"""Organisations — org table, users.org_id/org_role, Default-org backfill

Revision ID: 013
Revises: 012
Create Date: 2026-08-05
"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organisations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("invite_code", sa.String(36), nullable=False, unique=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "org_id",
            sa.String(36),
            sa.ForeignKey("organisations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("users", sa.Column("org_role", sa.String(10), nullable=True))
    op.create_index("ix_users_org_id", "users", ["org_id"])

    # Backfill: every pre-existing user joins a Default organisation so team
    # visibility keeps meaning "everyone who could read it before" on upgrade
    # (docs/09-organisations.md OQ-8). Fresh installs skip this — new users
    # register org-less.
    bind = op.get_bind()
    oldest = bind.execute(
        sa.text("SELECT id FROM users ORDER BY created_at, id LIMIT 1")
    ).scalar()
    if oldest is not None:
        org_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO organisations (id, name, invite_code, created_by) "
                "VALUES (:id, :name, :code, :creator)"
            ),
            {
                "id": org_id,
                "name": "Default organisation",
                "code": str(uuid.uuid4()),
                "creator": oldest,
            },
        )
        bind.execute(
            sa.text("UPDATE users SET org_id = :org, org_role = 'member'"),
            {"org": org_id},
        )
        bind.execute(
            sa.text("UPDATE users SET org_role = 'admin' WHERE id = :creator"),
            {"creator": oldest},
        )


def downgrade() -> None:
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_column("users", "org_role")
    op.drop_column("users", "org_id")
    op.drop_table("organisations")
