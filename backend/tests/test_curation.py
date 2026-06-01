"""Unit tests for curation domain — pure logic, no DB or Ollama."""

from app.domains.curation.types import build_fork_lineage


# ── build_fork_lineage ────────────────────────────────────────────────────────


def test_fork_lineage_from_root():
    result = build_fork_lineage([], "parent-id")
    assert result == ["parent-id"]


def test_fork_lineage_extends_existing():
    result = build_fork_lineage(["grandparent-id"], "parent-id")
    assert result == ["grandparent-id", "parent-id"]


def test_fork_lineage_does_not_mutate_parent():
    parent_lineage = ["grandparent-id"]
    build_fork_lineage(parent_lineage, "parent-id")
    assert parent_lineage == ["grandparent-id"]


def test_fork_lineage_deep_chain():
    result = build_fork_lineage(["a", "b", "c"], "d")
    assert result == ["a", "b", "c", "d"]
    assert len(result) == 4
