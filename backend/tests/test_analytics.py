"""Unit tests for path analytics shaping — pure logic, no DB (KC-082)."""

from datetime import datetime, timedelta, timezone

from app.domains.learning.analytics import _top_wrong_answers, build_analytics

_T0 = datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)


def _concepts(n: int) -> list[dict]:
    return [{"id": f"c{i}", "title": f"Concept {i}", "position": i} for i in range(n)]


def _progress(user_id: str, concept_id: str, minutes: int = 0) -> dict:
    return {"user_id": user_id, "concept_id": concept_id, "learned_at": _T0 + timedelta(minutes=minutes)}


def _attempt(user_id: str, concept_id: str, answer: str, correct: bool, label: str | None = None, minutes: int = 0) -> dict:
    return {
        "user_id": user_id,
        "concept_id": concept_id,
        "answer_text": answer,
        "correct": correct,
        "misconception_label": label,
        "created_at": _T0 + timedelta(minutes=minutes),
    }


_USERS = {
    "u1": {"id": "u1", "handle": "alice", "display_name": "Alice"},
    "u2": {"id": "u2", "handle": "bob", "display_name": "Bob"},
}


# ── build_analytics: learners ─────────────────────────────────────────────────


def test_learner_progress_and_correct_rate():
    result = build_analytics(
        _concepts(4),
        progress_rows=[_progress("u1", "c0"), _progress("u1", "c1")],
        attempt_rows=[
            _attempt("u1", "c0", "right", True),
            _attempt("u1", "c1", "wrong", False),
            _attempt("u1", "c1", "right", True, minutes=5),
        ],
        users=_USERS,
    )
    assert result["learner_count"] == 1
    l = result["learners"][0]
    assert l["user"]["handle"] == "alice"
    assert l["learned_count"] == 2
    assert l["completion_pct"] == 0.5
    assert l["attempt_count"] == 3
    assert l["correct_count"] == 2
    assert l["correct_rate"] == round(2 / 3, 4)
    assert l["last_activity"] == _T0 + timedelta(minutes=5)


def test_learners_sorted_by_progress_then_activity():
    result = build_analytics(
        _concepts(2),
        progress_rows=[_progress("u2", "c0"), _progress("u2", "c1")],
        attempt_rows=[_attempt("u1", "c0", "x", False)],
        users=_USERS,
    )
    assert [l["user"]["handle"] for l in result["learners"]] == ["bob", "alice"]


def test_learner_with_attempts_but_no_progress_included():
    result = build_analytics(
        _concepts(2),
        progress_rows=[],
        attempt_rows=[_attempt("u1", "c0", "x", False)],
        users=_USERS,
    )
    assert result["learner_count"] == 1
    assert result["learners"][0]["learned_count"] == 0
    assert result["learners"][0]["last_activity"] == _T0


def test_zero_active_concepts_no_division_error():
    result = build_analytics([], [], [], {})
    assert result["active_concept_count"] == 0
    assert result["learners"] == []
    assert result["concepts"] == []


# ── build_analytics: concepts ─────────────────────────────────────────────────


def test_concept_stats_and_top_wrong_answers():
    attempts = [
        _attempt("u1", "c0", "Compression", False, "confuses WAL with compression"),
        _attempt("u2", "c0", " compression ", False, "confuses WAL with compression"),
        _attempt("u1", "c0", "Replication", False),
        _attempt("u2", "c0", "Durability", True),
    ]
    result = build_analytics(_concepts(1), [_progress("u2", "c0")], attempts, _USERS)
    c = result["concepts"][0]
    assert c["learners_learned"] == 1
    assert c["attempt_count"] == 4
    assert c["correct_rate"] == 0.25
    top = c["top_wrong_answers"]
    assert top[0]["count"] == 2  # both compression variants grouped
    assert top[0]["misconception_label"] == "confuses WAL with compression"
    assert top[1]["answer_text"] == "Replication"


def test_concept_without_attempts_zero_rate():
    result = build_analytics(_concepts(1), [], [], {})
    c = result["concepts"][0]
    assert c["attempt_count"] == 0
    assert c["correct_rate"] == 0.0
    assert c["top_wrong_answers"] == []


# ── _top_wrong_answers ────────────────────────────────────────────────────────


def test_top_wrong_answers_caps_at_three():
    wrong = [_attempt("u1", "c0", f"answer {i}", False) for i in range(5)]
    assert len(_top_wrong_answers(wrong)) == 3


def test_top_wrong_answers_skips_empty_normalised():
    wrong = [_attempt("u1", "c0", "  !! ", False)]
    assert _top_wrong_answers(wrong) == []


def test_top_wrong_answers_first_label_wins_within_group():
    wrong = [
        _attempt("u1", "c0", "caching", False, None),
        _attempt("u2", "c0", "Caching", False, "confuses cache with WAL"),
    ]
    top = _top_wrong_answers(wrong)
    assert top[0]["count"] == 2
    assert top[0]["misconception_label"] == "confuses cache with WAL"
