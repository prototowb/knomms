"""Shared access predicates — team = same organisation (docs/09-organisations.md
OQ-7); per-resource ACL grants layered on top (docs/10-teams-and-acls.md OQ-16–18).

No read or write site may hand-roll visibility or grant subqueries — everything
goes through these helpers.
"""

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.acl import AclGrant
from app.models.team import TeamMembership
from app.models.user import User

GRANT_RESOURCE_TYPES = frozenset({"kb", "asset", "harness"})
GRANT_PRINCIPAL_TYPES = frozenset({"user", "team"})
GRANT_PERMISSIONS = frozenset({"viewer", "editor"})


def team_or_public_clause(model, user: User) -> ColumnElement:
    """Drop-in replacement for `model.visibility.in_(("team", "public"))`:
    public is readable by anyone; team only when the owner is in the reader's
    (non-NULL) org. Org-less readers get public only — NULL org must never act
    as one big shared org. Owner access stays the call site's own clause.

    `model` needs `visibility` and `owner_user_id` columns (KnowledgeBase,
    Asset, Harness — boards deliberately have no team reads, OQ-11).
    """
    public = model.visibility == "public"
    if user.org_id is None:
        return public
    same_org_owner = model.owner_user_id.in_(
        select(User.id).where(User.org_id == user.org_id)
    )
    return or_(public, and_(model.visibility == "team", same_org_owner))


def grant_subquery(
    resource_type: str,
    user: User,
    permissions: tuple[str, ...] = ("viewer", "editor"),
) -> Select:
    """resource_ids of `resource_type` granted to the user — directly or via a
    team they belong to. Editor implies viewer (OQ-16), hence the default tuple."""
    my_teams = select(TeamMembership.team_id).where(TeamMembership.user_id == user.id)
    return select(AclGrant.resource_id).where(
        AclGrant.resource_type == resource_type,
        AclGrant.permission.in_(permissions),
        or_(
            and_(AclGrant.principal_type == "user", AclGrant.principal_id == user.id),
            and_(AclGrant.principal_type == "team", AclGrant.principal_id.in_(my_teams)),
        ),
    )


def readable_clause(model, resource_type: str, user: User) -> ColumnElement:
    """Supersedes bare team_or_public_clause at the read sites: visibility rules
    OR an ACL grant of any permission. Owner access stays the call site's clause."""
    return or_(
        team_or_public_clause(model, user),
        model.id.in_(grant_subquery(resource_type, user)),
    )


async def has_grant(
    db,
    resource_type: str,
    resource_id: str,
    user: User,
    permissions: tuple[str, ...] = ("viewer", "editor"),
) -> bool:
    """Point check for services that load by primary key and compare owners
    (assets/harnesses) rather than filtering in the query."""
    result = await db.execute(
        grant_subquery(resource_type, user, permissions).where(
            AclGrant.resource_id == resource_id
        )
    )
    return result.first() is not None


def editable_clause(model, resource_type: str, user: User) -> ColumnElement:
    """Write guard for the OQ-18 surface: the owner OR an editor grant. Everything
    not enumerated in OQ-18 keeps the plain owner check."""
    return or_(
        model.owner_user_id == user.id,
        model.id.in_(grant_subquery(resource_type, user, permissions=("editor",))),
    )
