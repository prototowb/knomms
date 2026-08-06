"""Unit tests for mastery gate computation and payload shaping — pure logic, no DB (KC-088)."""

from app.domains.learning.gates import compute_gates, is_mastered
from app.domains.learning.router import _apply_gates
from app.schemas.learning import AssessmentItemOut, LearningPathOut, PathConceptOut

from datetime import datetime, timezone

_T0 = datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)


def _concept(cid: str, item_ids: list[str]) -> dict:
    return {"id": cid, "item_ids": item_ids}


# ── is_mastered ───────────────────────────────────────────────────────────────


def test_mastered_at_exact_threshold():
    mastered, correct = is_mastered(["i1", "i2", "i3", "i4", "i5"], {"i1", "i2", "i3", "i4"}, "c1", set(), 0.8)
    assert mastered is True
    assert correct == 4


def test_not_mastered_below_threshold():
    mastered, correct = is_mastered(["i1", "i2", "i3", "i4", "i5"], {"i1", "i2", "i3"}, "c1", set(), 0.8)
    assert mastered is False
    assert correct == 3


def test_no_items_falls_back_to_learned_mark():
    assert is_mastered([], set(), "c1", {"c1"}, 0.8) == (True, 0)
    assert is_mastered([], set(), "c1", set(), 0.8) == (False, 0)


def test_wrong_attempts_never_subtract():
    # Best-attempt semantics: correct_item_ids is the set of items ever
    # answered correctly — repeat wrong answers cannot unmaster a concept
    mastered, _ = is_mastered(["i1"], {"i1"}, "c1", set(), 1.0)
    assert mastered is True


# ── compute_gates ─────────────────────────────────────────────────────────────


def test_first_concept_never_locked():
    gates = compute_gates([_concept("c1", ["i1"]), _concept("c2", ["i2"])], set(), set(), 0.8)
    assert gates["c1"]["locked"] is False
    assert gates["c1"]["mastered"] is False
    assert gates["c2"]["locked"] is True


def test_unlock_cascade_as_concepts_are_mastered():
    concepts = [_concept("c1", ["i1"]), _concept("c2", ["i2"]), _concept("c3", ["i3"])]
    gates = compute_gates(concepts, {"i1"}, set(), 1.0)
    assert gates["c1"]["mastered"] is True
    assert gates["c2"]["locked"] is False
    assert gates["c3"]["locked"] is True  # c2 not yet mastered

    gates = compute_gates(concepts, {"i1", "i2"}, set(), 1.0)
    assert gates["c3"]["locked"] is False


def test_unmastered_middle_locks_everything_after():
    # c3 mastered by items, but c2 unmastered still locks it
    concepts = [_concept("c1", []), _concept("c2", ["i2"]), _concept("c3", ["i3"])]
    gates = compute_gates(concepts, {"i3"}, {"c1"}, 0.8)
    assert gates["c2"]["locked"] is False
    assert gates["c3"]["mastered"] is True
    assert gates["c3"]["locked"] is True


def test_itemless_concept_gates_on_learned_mark():
    concepts = [_concept("c1", []), _concept("c2", ["i2"])]
    assert compute_gates(concepts, set(), set(), 0.8)["c2"]["locked"] is True
    assert compute_gates(concepts, set(), {"c1"}, 0.8)["c2"]["locked"] is False


def test_empty_path():
    assert compute_gates([], set(), set(), 0.8) == {}


def test_counts_reported_per_concept():
    gates = compute_gates([_concept("c1", ["i1", "i2", "i3"])], {"i1", "ix"}, set(), 0.8)
    assert gates["c1"]["correct_items"] == 1
    assert gates["c1"]["item_count"] == 3


# ── _apply_gates payload shaping ──────────────────────────────────────────────


def _path_out(mode: str) -> LearningPathOut:
    return LearningPathOut(
        id="p1",
        kb_id="kb1",
        learning_goal="goal",
        status="published",
        version=1,
        mastery_mode=mode,
        mastery_threshold=0.8,
        created_at=_T0,
        updated_at=_T0,
        concepts=[
            PathConceptOut(
                id=f"c{i}",
                position=i,
                title=f"Concept {i}",
                explanation_text="secret content",
                explanation_passage_ids=["ch1"],
                source_passages=[{"chunk_id": "ch1", "excerpt": "secret"}],
                instructor_annotation="note",
                status="accepted",
                assessment_items=[
                    AssessmentItemOut(id=f"i{i}", question_text="q?", grounding_passage_id="ch1")
                ],
            )
            for i in range(2)
        ],
    )


_GATES = {
    "c0": {"mastered": False, "locked": False, "correct_items": 0, "item_count": 1},
    "c1": {"mastered": False, "locked": True, "correct_items": 0, "item_count": 1},
}


def test_apply_gates_none_is_noop():
    out = _path_out("hard")
    _apply_gates(out, None)
    assert out.concepts[1].locked is False
    assert out.concepts[1].gate is None
    assert out.concepts[1].explanation_text == "secret content"


def test_hard_mode_redacts_locked_concepts_only():
    out = _path_out("hard")
    _apply_gates(out, _GATES)
    open_c, locked_c = out.concepts
    assert open_c.locked is False
    assert open_c.explanation_text == "secret content"
    assert open_c.gate is not None and open_c.gate.item_count == 1
    assert locked_c.locked is True
    assert locked_c.explanation_text == ""
    assert locked_c.explanation_passage_ids == []
    assert locked_c.source_passages == []
    assert locked_c.assessment_items == []
    assert locked_c.instructor_annotation is None
    assert locked_c.title == "Concept 1"  # nav still renders


def test_soft_mode_marks_locked_but_never_redacts():
    out = _path_out("soft")
    _apply_gates(out, _GATES)
    assert out.concepts[1].locked is True
    assert out.concepts[1].explanation_text == "secret content"
    assert out.concepts[1].assessment_items != []


def test_pruned_concepts_absent_from_gates_untouched():
    out = _path_out("hard")
    _apply_gates(out, {"c0": _GATES["c0"]})  # c1 pruned → not in gates
    assert out.concepts[1].locked is False
    assert out.concepts[1].gate is None
    assert out.concepts[1].explanation_text == "secret content"
