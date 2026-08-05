"""Unit tests for organisation domain guards — pure logic, no DB."""

from app.domains.organisations.service import ORG_ROLES, demote_blocked, leave_blocked


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
