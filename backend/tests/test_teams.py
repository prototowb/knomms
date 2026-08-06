"""Unit tests for the team management guard (docs/10-teams-and-acls.md OQ-15)."""

from app.domains.organisations.teams import team_manage_allowed

# ── team_manage_allowed ──────────────────────────────────────────────────────


def test_org_admin_manages_any_team() -> None:
    assert team_manage_allowed(is_org_admin=True, is_creator=False) is True


def test_creator_manages_own_team() -> None:
    assert team_manage_allowed(is_org_admin=False, is_creator=True) is True


def test_admin_creator_manages() -> None:
    assert team_manage_allowed(is_org_admin=True, is_creator=True) is True


def test_plain_member_cannot_manage() -> None:
    assert team_manage_allowed(is_org_admin=False, is_creator=False) is False
