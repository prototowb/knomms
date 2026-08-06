"""Unit tests for discussion guards/anchoring — pure logic, no DB (KC-083)."""

import pytest

from app.domains.learning.discussions import can_delete_post, resolve_passage_anchor

_PASSAGES = [
    {"chunk_id": "ch1", "locator": "para:1", "source_id": "s1", "excerpt": "WAL ensures durability…"},
    {"chunk_id": "ch2", "locator": "para:2", "source_id": "s1", "excerpt": ""},
]


# ── resolve_passage_anchor ────────────────────────────────────────────────────


def test_anchor_none_returns_empty_excerpt():
    assert resolve_passage_anchor(None, _PASSAGES) == ""


def test_anchor_valid_returns_excerpt_snapshot():
    assert resolve_passage_anchor("ch1", _PASSAGES) == "WAL ensures durability…"


def test_anchor_valid_with_empty_excerpt():
    assert resolve_passage_anchor("ch2", _PASSAGES) == ""


def test_anchor_unknown_chunk_rejected():
    with pytest.raises(ValueError):
        resolve_passage_anchor("other-kb-chunk", _PASSAGES)


def test_anchor_rejected_when_concept_has_no_passages():
    with pytest.raises(ValueError):
        resolve_passage_anchor("ch1", [])
    with pytest.raises(ValueError):
        resolve_passage_anchor("ch1", None)


# ── can_delete_post ───────────────────────────────────────────────────────────


def test_author_deletes_own_post():
    assert can_delete_post("u1", "u1", "owner") is True


def test_path_owner_moderates_any_post():
    assert can_delete_post("u1", "owner", "owner") is True


def test_other_reader_cannot_delete():
    assert can_delete_post("u1", "u2", "owner") is False
