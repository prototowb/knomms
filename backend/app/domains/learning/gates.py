"""Mastery gate computation (docs/14, OQ-46/47) — pure, no DB.

Gates operate on the non-pruned concept sequence: a concept is locked while
any earlier concept is unmastered. Mastery is best-attempt over a concept's
assessment items (fraction of items answered correctly at least once meets
the threshold); concepts without items fall back to the learner's own
learned mark. The path owner is exempt at the call site — these functions
never see owner requests.
"""


def is_mastered(
    item_ids: list[str],
    correct_item_ids: set[str],
    concept_id: str,
    learned_concept_ids: set[str],
    threshold: float,
) -> tuple[bool, int]:
    """Whether one concept is mastered; returns (mastered, correct_item_count)."""
    if not item_ids:
        return concept_id in learned_concept_ids, 0
    correct = sum(1 for i in item_ids if i in correct_item_ids)
    return (correct / len(item_ids)) >= threshold, correct


def compute_gates(
    concepts: list[dict],
    correct_item_ids: set[str],
    learned_concept_ids: set[str],
    threshold: float,
) -> dict[str, dict]:
    """Gate state per concept for one learner.

    `concepts` is the path's non-pruned sequence in position order, each
    `{"id": str, "item_ids": list[str]}`. Returns
    `{concept_id: {mastered, locked, correct_items, item_count}}`; the first
    concept is never locked, and each later concept is locked while any
    earlier one is unmastered.
    """
    result: dict[str, dict] = {}
    blocked = False
    for concept in concepts:
        item_ids = concept["item_ids"]
        mastered, correct = is_mastered(
            item_ids, correct_item_ids, concept["id"], learned_concept_ids, threshold
        )
        result[concept["id"]] = {
            "mastered": mastered,
            "locked": blocked,
            "correct_items": correct,
            "item_count": len(item_ids),
        }
        blocked = blocked or not mastered
    return result
