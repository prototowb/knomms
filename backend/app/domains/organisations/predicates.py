"""Shared visibility predicate — team = same organisation (docs/09-organisations.md OQ-7)."""

from sqlalchemy import and_, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.user import User


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
