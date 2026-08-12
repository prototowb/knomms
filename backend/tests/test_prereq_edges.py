"""Unit tests for prerequisite edge sanitization — pure logic, no DB (KC-107)."""

from app.domains.learning.gates import MAX_PREREQS_PER_CONCEPT, sanitize_edges


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
