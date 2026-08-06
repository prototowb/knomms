"""Pure shaping for path comprehension analytics (docs/13, OQ-39) — no DB, no I/O.

The service layer feeds plain dicts; this module aggregates them into the
owner-facing analytics shape (docs/03 §5.4: mastery distribution, attempt
stats, common wrong answers with misconception labels).
"""

from app.domains.learning.service import _normalize_answer

TOP_WRONG_ANSWERS = 3


def build_analytics(
    active_concepts: list[dict],
    progress_rows: list[dict],
    attempt_rows: list[dict],
    users: dict[str, dict],
) -> dict:
    """Aggregate per-learner and per-concept analytics.

    active_concepts: [{id, title, position}] — non-pruned, in path order.
    progress_rows:   [{user_id, concept_id, learned_at}] — scoped to active concepts.
    attempt_rows:    [{user_id, concept_id, answer_text, correct, misconception_label, created_at}]
                     — scoped to the path's active concepts.
    users:           user_id → {id, handle, display_name} for every id above.
    """
    active_ids = [c["id"] for c in active_concepts]
    active_count = len(active_ids)

    # ── per learner ───────────────────────────────────────────────────────────
    learner_ids = sorted({r["user_id"] for r in progress_rows} | {a["user_id"] for a in attempt_rows})
    learners = []
    for uid in learner_ids:
        learned = [r for r in progress_rows if r["user_id"] == uid]
        attempts = [a for a in attempt_rows if a["user_id"] == uid]
        correct = sum(1 for a in attempts if a["correct"])
        activity_times = [r["learned_at"] for r in learned] + [a["created_at"] for a in attempts]
        learners.append(
            {
                "user": users.get(uid, {"id": uid, "handle": "?", "display_name": "Unknown"}),
                "learned_count": len(learned),
                "completion_pct": round(len(learned) / active_count, 4) if active_count else 0.0,
                "attempt_count": len(attempts),
                "correct_count": correct,
                "correct_rate": round(correct / len(attempts), 4) if attempts else 0.0,
                "last_activity": max(activity_times) if activity_times else None,
            }
        )
    # Most complete first, then most active — the instructor's scan order
    learners.sort(key=lambda l: (-l["learned_count"], -l["attempt_count"]))

    # ── per concept ───────────────────────────────────────────────────────────
    concepts = []
    for c in active_concepts:
        cid = c["id"]
        c_attempts = [a for a in attempt_rows if a["concept_id"] == cid]
        correct = sum(1 for a in c_attempts if a["correct"])
        concepts.append(
            {
                "concept_id": cid,
                "title": c["title"],
                "position": c["position"],
                "learners_learned": sum(1 for r in progress_rows if r["concept_id"] == cid),
                "attempt_count": len(c_attempts),
                "correct_rate": round(correct / len(c_attempts), 4) if c_attempts else 0.0,
                "top_wrong_answers": _top_wrong_answers([a for a in c_attempts if not a["correct"]]),
            }
        )

    return {
        "active_concept_count": active_count,
        "learner_count": len(learners),
        "learners": learners,
        "concepts": concepts,
    }


def _top_wrong_answers(wrong_attempts: list[dict]) -> list[dict]:
    """Group wrong attempts by normalised answer text; top N by count.

    The display text is the first-seen raw form; the misconception label is
    the first non-null label in the group (labels come from the matched
    distractor, so a group has at most one distinct label in practice).
    """
    groups: dict[str, dict] = {}
    for a in wrong_attempts:
        key = _normalize_answer(a["answer_text"])
        if not key:
            continue
        g = groups.setdefault(key, {"answer_text": a["answer_text"], "count": 0, "misconception_label": None})
        g["count"] += 1
        if g["misconception_label"] is None and a.get("misconception_label"):
            g["misconception_label"] = a["misconception_label"]
    ranked = sorted(groups.values(), key=lambda g: (-g["count"], _normalize_answer(g["answer_text"])))
    return ranked[:TOP_WRONG_ANSWERS]
