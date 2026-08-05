"""Unit tests for organisation domain guards and predicates — pure logic, no DB."""

from types import SimpleNamespace

from app.domains.organisations.predicates import team_or_public_clause
from app.domains.organisations.service import ORG_ROLES, demote_blocked, leave_blocked
from app.models.knowledge_base import KnowledgeBase


# ── leave_blocked ─────────────────────────────────────────────────────────────


def test_member_can_always_leave():
    assert leave_blocked(is_admin=False, admin_count=1, member_count=5) is False


def test_last_admin_cannot_leave_with_members_remaining():
    assert leave_blocked(is_admin=True, admin_count=1, member_count=3) is True


def test_last_admin_can_leave_when_sole_member():
    # Leaving empties the org — nobody is stranded
    assert leave_blocked(is_admin=True, admin_count=1, member_count=1) is False


def test_admin_can_leave_when_another_admin_exists():
    assert leave_blocked(is_admin=True, admin_count=2, member_count=4) is False


# ── demote_blocked ────────────────────────────────────────────────────────────


def test_cannot_demote_last_admin():
    assert demote_blocked(target_is_admin=True, admin_count=1) is True


def test_can_demote_admin_when_another_exists():
    assert demote_blocked(target_is_admin=True, admin_count=2) is False


def test_demoting_member_is_noop_guard():
    # Demoting someone who is already a member never trips the guard
    assert demote_blocked(target_is_admin=False, admin_count=1) is False


# ── role vocabulary ───────────────────────────────────────────────────────────


def test_org_roles_exactly_admin_and_member():
    assert ORG_ROLES == {"admin", "member"}


# ── team_or_public_clause ─────────────────────────────────────────────────────
# The helper reads only user.org_id, so a stub suffices; assertions are on the
# compiled SQL shape (postgres dialect not needed for these constructs).


def _sql(user) -> str:
    clause = team_or_public_clause(KnowledgeBase, user)
    return str(clause.compile(compile_kwargs={"literal_binds": True}))


def test_orgless_reader_gets_public_only():
    sql = _sql(SimpleNamespace(org_id=None))
    assert "'public'" in sql
    assert "team" not in sql
    assert "users" not in sql  # no org subquery for org-less readers


def test_org_reader_gets_public_or_same_org_team():
    sql = _sql(SimpleNamespace(org_id="org-123"))
    assert "'public'" in sql
    assert "'team'" in sql
    assert "'org-123'" in sql
    # team access goes through owner-in-my-org, not a visibility check alone
    assert "owner_user_id IN" in sql and "users.org_id" in sql


def test_team_never_leaks_without_org_match():
    # The team arm must be AND-ed with the same-org subquery — a bare
    # visibility = 'team' disjunct would reopen the OQ-3 hole
    sql = _sql(SimpleNamespace(org_id="org-123"))
    team_pos = sql.index("'team'")
    and_tail = sql[team_pos:]
    assert "AND" in and_tail and "users.org_id" in and_tail
