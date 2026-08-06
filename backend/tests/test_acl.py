"""Unit tests for the ACL predicates and grant guards (docs/10-teams-and-acls.md).

Same technique as test_organisations.py: compile clauses to SQL text and assert
on shape — no DB needed.
"""

from types import SimpleNamespace

from app.domains.acl.service import grant_upsert_allowed
from app.domains.organisations.predicates import (
    GRANT_PERMISSIONS,
    GRANT_PRINCIPAL_TYPES,
    GRANT_RESOURCE_TYPES,
    editable_clause,
    grant_subquery,
    readable_clause,
)
from app.models.knowledge_base import KnowledgeBase


def _sql(clause) -> str:
    return str(clause.compile(compile_kwargs={"literal_binds": True}))


ORG_USER = SimpleNamespace(id="u-1", org_id="org-1")
LONE_USER = SimpleNamespace(id="u-2", org_id=None)

# ── grant_subquery ───────────────────────────────────────────────────────────


def test_grant_subquery_covers_user_and_team_principals() -> None:
    sql = _sql(grant_subquery("kb", ORG_USER))
    assert "acl_grants" in sql
    assert "'user'" in sql and "'team'" in sql
    assert "team_memberships" in sql  # team reach goes through membership


def test_grant_subquery_default_permissions_include_both() -> None:
    sql = _sql(grant_subquery("kb", ORG_USER))
    assert "'viewer'" in sql and "'editor'" in sql  # editor implies viewer


def test_grant_subquery_editor_only_excludes_viewer() -> None:
    sql = _sql(grant_subquery("kb", ORG_USER, permissions=("editor",)))
    assert "'editor'" in sql and "'viewer'" not in sql


def test_grant_subquery_scopes_resource_type() -> None:
    sql = _sql(grant_subquery("harness", ORG_USER))
    assert "'harness'" in sql


# ── readable_clause ──────────────────────────────────────────────────────────


def test_readable_clause_is_visibility_or_grant() -> None:
    sql = _sql(readable_clause(KnowledgeBase, "kb", ORG_USER))
    # visibility layer intact...
    assert "'public'" in sql and "'team'" in sql and "users.org_id" in sql
    # ...plus the grant layer
    assert "acl_grants" in sql


def test_readable_clause_orgless_user_keeps_grants() -> None:
    # An org-less user reads public + anything granted to them — the NULL-org
    # guard must not strip the grant disjunct
    sql = _sql(readable_clause(KnowledgeBase, "kb", LONE_USER))
    assert "'public'" in sql
    assert "acl_grants" in sql
    assert "users.org_id" not in sql  # no org subquery for org-less readers


# ── editable_clause ──────────────────────────────────────────────────────────


def test_editable_clause_owner_or_editor_grant_only() -> None:
    sql = _sql(editable_clause(KnowledgeBase, "kb", ORG_USER))
    assert "owner_user_id" in sql
    assert "'editor'" in sql
    assert "'viewer'" not in sql  # viewers must never write
    assert "'public'" not in sql  # visibility never grants writes


# ── vocabularies & guards ────────────────────────────────────────────────────


def test_grant_vocabularies() -> None:
    assert GRANT_RESOURCE_TYPES == {"kb", "asset", "harness"}
    assert GRANT_PRINCIPAL_TYPES == {"user", "team"}
    assert GRANT_PERMISSIONS == {"viewer", "editor"}


def test_grant_upsert_requires_owner() -> None:
    assert grant_upsert_allowed(is_owner=True, principal_is_owner=False) is True
    assert grant_upsert_allowed(is_owner=False, principal_is_owner=False) is False


def test_grant_to_owner_is_refused() -> None:
    assert grant_upsert_allowed(is_owner=True, principal_is_owner=True) is False
