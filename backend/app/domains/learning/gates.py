"""Mastery gate computation (docs/14, OQ-46/47) — pure, no DB.

Gates operate on the non-pruned concept sequence: a concept is locked while
any earlier concept is unmastered. Mastery is best-attempt over a concept's
assessment items (fraction of items answered correctly at least once meets
the threshold); concepts without items fall back to the learner's own
learned mark. The path owner is exempt at the call site — these functions
never see owner requests.
"""


STRENGTHS = ("required", "recommended")
MAX_PREREQS_PER_CONCEPT = 3


def sanitize_edges(concept_count: int, raw_edges: list) -> dict[int, list[dict]]:
    """Model-proposed edges → a DAG by construction (docs/19, OQ-84). Pure.

    Drops self-edges, out-of-range indexes, over-cap prerequisites, and any
    edge that would close a cycle (edges are considered in model order, so
    the drop is deterministic). Duplicates keep the strongest strength.
    Returns {dependent_index: [{prereq_index, strength, rationale}]}.
    """
    fwd: dict[int, set[int]] = {}  # prereq → dependents (edge direction)
    result: dict[int, list[dict]] = {}

    def _reachable(start: int, target: int) -> bool:
        stack, visited = [start], set()
        while stack:
            node = stack.pop()
            if node == target:
                return True
            if node in visited:
                continue
            visited.add(node)
            stack.extend(fwd.get(node, ()))
        return False

    for edge in raw_edges or []:
        if not isinstance(edge, dict):
            continue
        frm, to = edge.get("from"), edge.get("to")
        if not isinstance(frm, int) or not isinstance(to, int) or isinstance(frm, bool) or isinstance(to, bool):
            continue
        if frm == to or not (0 <= frm < concept_count) or not (0 <= to < concept_count):
            continue
        strength = edge.get("strength") if edge.get("strength") in STRENGTHS else "recommended"
        rationale = str(edge.get("rationale") or "")[:300]

        existing = next((p for p in result.get(to, []) if p["prereq_index"] == frm), None)
        if existing is not None:
            if existing["strength"] == "recommended" and strength == "required":
                existing["strength"] = strength  # duplicate: keep the strongest
            continue
        if len(result.get(to, [])) >= MAX_PREREQS_PER_CONCEPT:
            continue
        if _reachable(to, frm):  # a path to→…→frm exists; frm→to would close a cycle
            continue

        fwd.setdefault(frm, set()).add(to)
        result.setdefault(to, []).append(
            {"prereq_index": frm, "strength": strength, "rationale": rationale}
        )
    return result


def validate_edge_update(
    existing_prereqs_by_id: dict[str, list[dict]],
    concept_id: str,
    new_prereqs: list,
) -> str | None:
    """Instructor-proposed prerequisite replacement → precise error, or None
    if valid (docs/20, OQ-88). Pure.

    Id-based twin of `sanitize_edges`, but *rejecting* instead of dropping:
    a human edit deserves an error, not silent repair. `existing_prereqs_by_id`
    maps every non-pruned sibling concept id in the path to its current
    prerequisites list (`[{concept_id, strength, rationale}]`); the graph
    formed by all OTHER concepts' existing edges plus the new list for
    `concept_id` must stay acyclic.
    """
    if len(new_prereqs or []) > MAX_PREREQS_PER_CONCEPT:
        return f"A concept can have at most {MAX_PREREQS_PER_CONCEPT} prerequisites"

    seen: set[str] = set()
    for entry in new_prereqs or []:
        if not isinstance(entry, dict):
            return "Each prerequisite must be an object with concept_id and strength"
        prereq_id = entry.get("concept_id")
        if prereq_id == concept_id:
            return "A concept cannot be its own prerequisite"
        if prereq_id not in existing_prereqs_by_id:
            return f"Prerequisite {prereq_id!r} is not a non-pruned concept in this path"
        if prereq_id in seen:
            return f"Duplicate prerequisite: {prereq_id!r}"
        seen.add(prereq_id)
        if entry.get("strength") not in STRENGTHS:
            return "Prerequisite strength must be 'required' or 'recommended'"
        rationale = entry.get("rationale")
        if rationale is not None and not isinstance(rationale, str):
            return "Prerequisite rationale must be a string"
        if rationale is not None and len(rationale) > 300:
            return "Prerequisite rationale must be at most 300 characters"

    # Cycle check over string ids (adapted from sanitize_edges): every OTHER
    # concept keeps its existing edges; the edited concept's edges are the
    # new list wholesale. Edge direction is prereq → dependent.
    fwd: dict[str, set[str]] = {}
    for dependent, prereqs in existing_prereqs_by_id.items():
        if dependent == concept_id:
            continue  # replaced wholesale by new_prereqs
        for p in prereqs or []:
            fwd.setdefault(p.get("concept_id"), set()).add(dependent)

    def _reachable(start: str, target: str) -> bool:
        stack, visited = [start], set()
        while stack:
            node = stack.pop()
            if node == target:
                return True
            if node in visited:
                continue
            visited.add(node)
            stack.extend(fwd.get(node, ()))
        return False

    for entry in new_prereqs or []:
        prereq_id = entry["concept_id"]
        # A path concept_id→…→prereq_id exists, so prereq_id→concept_id
        # would close a cycle.
        if _reachable(concept_id, prereq_id):
            return f"Prerequisite {prereq_id!r} would create a cycle"
    return None


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
    `{"id": str, "item_ids": list[str], "prerequisites": list[dict]}`.
    Returns `{concept_id: {mastered, locked, correct_items, item_count}}`.

    Graph mode (docs/19, OQ-85): when the path has any prerequisite edges, a
    concept is locked iff any of its **required**, non-pruned prerequisites
    is unmastered — concepts without required prerequisites are never
    locked, and `recommended` edges never lock. Paths with no edges keep
    the v0.11.0 sequence rule (each concept locked while any earlier one
    is unmastered; the first is never locked).
    """
    result: dict[str, dict] = {}
    for concept in concepts:
        item_ids = concept["item_ids"]
        mastered, correct = is_mastered(
            item_ids, correct_item_ids, concept["id"], learned_concept_ids, threshold
        )
        result[concept["id"]] = {
            "mastered": mastered,
            "locked": False,
            "correct_items": correct,
            "item_count": len(item_ids),
        }

    if any(concept.get("prerequisites") for concept in concepts):
        for concept in concepts:
            required = [
                p.get("concept_id")
                for p in (concept.get("prerequisites") or [])
                if p.get("strength") == "required"
            ]
            # Prereqs absent from result are pruned — they neither gate nor lock
            result[concept["id"]]["locked"] = any(
                pid in result and not result[pid]["mastered"] for pid in required
            )
    else:
        blocked = False
        for concept in concepts:
            result[concept["id"]]["locked"] = blocked
            blocked = blocked or not result[concept["id"]]["mastered"]
    return result
