"""Board visibility validation — boards are private|public only (KC-116, docs/22 OQ-94)."""

import pytest
from fastapi import HTTPException

from app.domains.curation.router import _validate_board_visibility


def test_private_and_public_accepted():
    _validate_board_visibility("private")
    _validate_board_visibility("public")


def test_team_rejected_with_design_pointer():
    with pytest.raises(HTTPException) as exc:
        _validate_board_visibility("team")
    assert exc.value.status_code == 422
    assert "excluded by design" in exc.value.detail


def test_garbage_rejected():
    with pytest.raises(HTTPException):
        _validate_board_visibility("everyone")
