"""Teams & ACL grants — teams, team_memberships, acl_grants

Revision ID: 014
Revises: 013
Create Date: 2026-08-06
"""

import sqlalchemy as sa
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "org_id",
            sa.String(36),
            sa.ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("org_id", "name", name="uq_teams_org_id_name"),
    )
    op.create_index("ix_teams_org_id", "teams", ["org_id"])

    op.create_table(
        "team_memberships",
        sa.Column(
            "team_id",
            sa.String(36),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("added_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_team_memberships_user_id", "team_memberships", ["user_id"])

    op.create_table(
        "acl_grants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource_type", sa.String(10), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("principal_type", sa.String(10), nullable=False),
        sa.Column("principal_id", sa.String(36), nullable=False),
        sa.Column("permission", sa.String(10), nullable=False),
        sa.Column("granted_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "resource_type",
            "resource_id",
            "principal_type",
            "principal_id",
            name="uq_acl_grants_resource_principal",
        ),
    )
    op.create_index("ix_acl_grants_principal", "acl_grants", ["principal_type", "principal_id"])
    op.create_index("ix_acl_grants_resource", "acl_grants", ["resource_type", "resource_id"])

    # No backfill — all three tables start empty on both fresh installs and
    # upgrades (docs/10-teams-and-acls.md §4).


def downgrade() -> None:
    op.drop_index("ix_acl_grants_resource", table_name="acl_grants")
    op.drop_index("ix_acl_grants_principal", table_name="acl_grants")
    op.drop_table("acl_grants")
    op.drop_index("ix_team_memberships_user_id", table_name="team_memberships")
    op.drop_table("team_memberships")
    op.drop_index("ix_teams_org_id", table_name="teams")
    op.drop_table("teams")
