"""Unit tests for prerequisite edge sanitization — pure logic, no DB (KC-107)."""

from app.domains.learning.gates import (
    MAX_PREREQS_PER_CONCEPT,
    sanitize_edges,
    validate_edge_update,
)


def _e(frm, to, strength="required", rationale="because"):
    return {"from": frm, "to": to, "strength": strength, "rationale": rationale}


def test_valid_edges_grouped_by_dependent():
    result = sanitize_edges(3, [_e(0, 2), _e(1, 2, "recommended")])
    assert set(result) == {2}
    assert [p["prereq_index"] for p in result[2]] == [0, 1]
    assert result[2][1]["strength"] == "recommended"


def test_garbage_dropped():
    result = sanitize_edges(3, [
        _e(0, 0),                # self
        _e(5, 1), _e(1, 9),      # out of range
        _e(True, 1),             # bool masquerading as int
        {"from": "0", "to": 1},  # wrong types
        "not a dict",
        _e(0, 1),                # the one keeper
    ])
    assert set(result) == {1}
    assert len(result[1]) == 1


def test_unknown_strength_degrades_to_recommended():
    result = sanitize_edges(2, [_e(0, 1, strength="mandatory")])
    assert result[1][0]["strength"] == "recommended"


def test_duplicate_keeps_strongest():
    result = sanitize_edges(2, [_e(0, 1, "recommended"), _e(0, 1, "required")])
    assert len(result[1]) == 1
    assert result[1][0]["strength"] == "required"


def test_cap_per_concept():
    edges = [_e(i, 5) for i in range(5)]
    result = sanitize_edges(6, edges)
    assert len(result[5]) == MAX_PREREQS_PER_CONCEPT


def test_cycle_closing_edge_dropped():
    # 0→1, 1→2 accepted; 2→0 would close a cycle and must be dropped
    result = sanitize_edges(3, [_e(0, 1), _e(1, 2), _e(2, 0)])
    assert 0 not in result
    assert set(result) == {1, 2}


def test_two_edge_cycle_dropped():
    result = sanitize_edges(2, [_e(0, 1), _e(1, 0)])
    assert set(result) == {1}


def test_rationale_truncated():
    result = sanitize_edges(2, [_e(0, 1, rationale="x" * 500)])
    assert len(result[1][0]["rationale"]) == 300


def test_empty_and_none_input():
    assert sanitize_edges(3, []) == {}
    assert sanitize_edges(3, None) == {}


# ── validate_edge_update — instructor edits (KC-111, docs/20 OQ-88) ─────────


def _p(concept_id, strength="required", rationale=""):
    return {"concept_id": concept_id, "strength": strength, "rationale": rationale}


def _siblings(**prereqs):
    """{"a": [], "b": [...], ...} — every non-pruned concept in the path."""
    base = {cid: [] for cid in ("a", "b", "c", "d", "e")}
    base.update(prereqs)
    return base


def test_edge_update_valid_returns_none():
    existing = _siblings(b=[_p("a")])
    assert validate_edge_update(existing, "c", [_p("a"), _p("b", "recommended", "builds on it")]) is None


def test_edge_update_empty_list_clears_edges():
    assert validate_edge_update(_siblings(b=[_p("a")]), "b", []) is None


def test_edge_update_self_edge_rejected():
    error = validate_edge_update(_siblings(), "a", [_p("a")])
    assert error is not None and "own prerequisite" in error


def test_edge_update_non_sibling_rejected():
    error = validate_edge_update(_siblings(), "a", [_p("zzz")])
    assert error is not None and "not a non-pruned concept" in error


def test_edge_update_over_cap_rejected():
    error = validate_edge_update(_siblings(), "e", [_p("a"), _p("b"), _p("c"), _p("d")])
    assert error is not None and str(MAX_PREREQS_PER_CONCEPT) in error


def test_edge_update_duplicate_rejected():
    error = validate_edge_update(_siblings(), "c", [_p("a"), _p("a", "recommended")])
    assert error is not None and "Duplicate" in error


def test_edge_update_bad_strength_rejected():
    error = validate_edge_update(_siblings(), "b", [_p("a", strength="mandatory")])
    assert error is not None and "strength" in error


def test_edge_update_long_rationale_rejected():
    error = validate_edge_update(_siblings(), "b", [_p("a", rationale="x" * 301)])
    assert error is not None and "300" in error


def test_edge_update_non_dict_entry_rejected():
    error = validate_edge_update(_siblings(), "b", ["a"])
    assert error is not None and "object" in error


def test_edge_update_cycle_against_existing_edges_rejected():
    # Existing: b requires a. New edit: a requires b → a→b→a cycle.
    error = validate_edge_update(_siblings(b=[_p("a")]), "a", [_p("b")])
    assert error is not None and "cycle" in error


def test_edge_update_transitive_cycle_rejected():
    # Existing: b requires a, c requires b. New edit: a requires c.
    error = validate_edge_update(_siblings(b=[_p("a")], c=[_p("b")]), "a", [_p("c")])
    assert error is not None and "cycle" in error


def test_edge_update_replacing_edges_breaks_would_be_cycle():
    # Existing: b requires a — so "a requires b" is a cycle. But once b's
    # edges are replaced (b now requires c), "a requires b" becomes legal:
    # the edited concept's own old edges must not count against it.
    assert validate_edge_update(_siblings(b=[_p("a")]), "b", [_p("c")]) is None
    assert validate_edge_update(_siblings(b=[_p("c")]), "a", [_p("b")]) is None
