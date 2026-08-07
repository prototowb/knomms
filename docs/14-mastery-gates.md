# Mastery Gates — Cohort Learning, Part 2 (Design)

> Status: **proposed** (2026-08-06). Second slice of the V2 cohort-learning
> priority. Part 1 (`docs/13-cohort-learning.md`, v0.10.0) shipped persisted
> attempts, owner analytics, and passage-anchored discussion; this part ships
> the deferred **mastery gates** (docs/13 §7, spec §4.4 of
> `docs/03-learning-layer.md`) plus the small "N learners" badge the analytics
> data now makes cheap. Proposed sprint: **v0.11.0 = KC-087–091**.

## 1. Problem

A path owner can now *see* who is stuck (v0.10.0 analytics) but cannot *shape
the learner flow*: every concept is open from the first page load, so a
learner can skip to concept 5 with nothing understood, and the spec's
instructor promise — "set mastery thresholds → publish to cohort" (§2.3 core
flow) — has no mechanism behind it. §4.4 defines the shape: a learner cannot
advance past a gate until their mastery score meets the threshold, with a
`soft` variant that warns instead of blocking.

## 2. What exists to build on

- **Persisted attempts** (`assessment_attempts`, v0.10.0) — per-(user, item)
  correctness history; mastery is computable server-side, per request, with
  one query. This is why gates were part 2: before v0.10.0 there was no data.
- **Flat concept sequence** — the implemented model has ordered
  `path_concepts`, not the spec's module hierarchy or prerequisite graph
  (curriculum groups per source since KC-074). Gates therefore operate on the
  **sequence**: concept N is gated by concepts 1…N-1, not by graph edges.
- **Learner/owner split** — `get_readable_path` vs `get_path`, and
  `_shape_assessment_items` already reshapes the payload per role; locked-
  concept redaction extends the same hook.

## 3. Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-45 | Gate configuration | Two columns on `learning_paths` (Migration 018): `mastery_mode` String(10) NOT NULL default `'off'` (`off\|soft\|hard`) and `mastery_threshold` Float NOT NULL default `0.8`. Owner sets both via new `PATCH /v1/learning-paths/{id}` (metadata-PATCH precedent, KC-056); 422 on unknown mode or threshold outside (0, 1] | Path-level, not per-concept: the implemented model is a flat sequence, one knob is the smallest honest slice of §4.4's per-module thresholds. Default `off` = byte-identical behaviour for every existing path (the OQ-2 discipline) |
| OQ-46 | Mastery definition | Per (user, concept): if the concept has assessment items, mastered ⇔ `distinct items answered correctly at least once / item count ≥ threshold` (best-attempt semantics — wrong tries never subtract); if it has **no** items, mastered ⇔ learner marked it learned | §4.4 derives mastery from assessments; self-report is only the fallback where no assessment exists. Best-attempt (not rolling rate) so a learner can always work their way through a gate — a rolling correct-rate can become unrecoverable |
| OQ-47 | What locks | Non-pruned concepts in position order; concept N is **locked** iff any earlier non-pruned concept is not mastered. First non-pruned concept is never locked. Pruned concepts neither gate nor lock. The **path owner is always exempt** | Sequence semantics (see §2). Owner exemption: gates shape the learner flow; the instructor is editing it |
| OQ-48 | Enforcement by mode | `off`: nothing computed, payload unchanged. `soft`: gate state shipped in the payload; UI warns on locked concepts; server blocks nothing. `hard`: gate state shipped **and** locked concepts are redacted in the learner payload (explanation, passages, annotation, assessment items emptied; title/position/status stay so the nav renders) **and** the server rejects attempt, learned-mark/unmark, thread list/create, and thread read on locked concepts with **422 "Concept is locked by mastery gating"** | Redaction is what makes `hard` honest — a 422 on attempts alone would still hand the content to anyone with curl. Thread reads are gated too because thread bodies/excerpts quote locked passages. 422 (not 404): the learner legitimately knows the concept exists — it's in their nav; the codebase reserves 404 for non-leak authz |
| OQ-49 | Where gate state is computed | Server-side per request, in the learner path GET (and in the guard helper for writes). One extra query per request — distinct correct `(item_id)` per user over the path's items — **only when `mastery_mode != 'off'`**. Payload: `LearningPathOut` gains `mastery_mode` + `mastery_threshold`; `PathConceptOut` gains `locked: bool` and `gate: {mastered, correct_items, item_count} \| null` (null when mode is off) | Fresh-per-request matches every other authz decision (OQ-10/13 immediacy — no cached lock state to invalidate). Zero cost on the default path |
| OQ-50 | Gate checks on deletes | Post/thread deletion is **not** gated | Deleting your own content exposes nothing; blocking it would strand a learner's post if the owner tightens the gate later |
| OQ-51 | Learner-count badge | `LearningPathSummary` gains `learner_count` = distinct users with a `concept_progress` row or an `assessment_attempt` on the path (owner included when active). Visible to every reader of the list | Count ≠ roster: identities stay owner-only (OQ-39); a bare count is the classic social signal and the backlog's cheapest analytics payoff |
| OQ-52 | No override valve | §4.4's `gate_override_after_days` is **not** in this slice | It needs per-(user, concept) first-blocked timestamps — new table, new semantics. The owner switching to `soft` is the manual valve; revisit if real cohorts hit walls |

## 4. Schema (Migration 018)

```
learning_paths (altered)
  mastery_mode       String(10) NOT NULL DEFAULT 'off'   -- off | soft | hard
  mastery_threshold  Float      NOT NULL DEFAULT 0.8     -- fraction of items, (0, 1]
```

`downgrade()` drops both columns.

## 5. Backend changes

- **Pure gate logic** — new `learning/gates.py`:
  `compute_gates(concepts, correct_item_ids, learned_concept_ids, threshold)`
  → `{concept_id: {mastered, locked, correct_items, item_count}}`, where
  `concepts` is the non-pruned sequence with per-concept item id lists.
  Pure function, fully unit-tested (threshold boundary, no-items fallback,
  pruned exclusion, first-concept never locked, empty path).
- **Service** (`learning/service.py`):
  - `update_path(path_id, user, *, mastery_mode, mastery_threshold)` — owner
    guard via `get_path`, validation (mode ∈ off/soft/hard, 0 < threshold ≤ 1).
  - `gate_states(path, user)` — fetches the user's distinct correct item ids
    (`assessment_attempts` WHERE path/user/correct) + learned ids, delegates
    to `compute_gates`. Returns `None` when mode is off or user is the owner
    (owner exemption, OQ-47).
  - `_ensure_not_locked(path_id, concept_id, user)` — raises 422 in hard mode
    when the concept is locked; called by `grade_attempt`, `set_learned`, and
    the discussion read/create paths (via DiscussionService).
- **Router**:
  - `PATCH /v1/learning-paths/{path_id}` — owner-only metadata PATCH
    (`mastery_mode`, `mastery_threshold`), returns `LearningPathOut`.
  - Path GET: compute gate states for non-owner readers when mode ≠ off;
    stamp `locked`/`gate` per concept; in hard mode redact locked concepts
    (empty `explanation_text`, `explanation_passage_ids`, `source_passages`,
    `assessment_items`; null `instructor_annotation`).
- **Schemas**: `LearningPathOut` + `mastery_mode`/`mastery_threshold`;
  `PathConceptOut` + `locked`/`gate`; new `ConceptGateOut`,
  `UpdatePathRequest`; `LearningPathSummary` + `learner_count` (OQ-51).
- **Attempt response unchanged** — gates change *whether* an attempt is
  accepted, never the grading contract.

## 6. Frontend changes

- **Owner controls** (learn page top bar / settings row): mastery-gate mode
  select (`Off / Soft / Hard`) + threshold input (percent), PATCH on change;
  visible to the owner only.
- **Learner locked UI**: lock glyph in the concept nav for locked concepts;
  locked concept body replaced by a locked panel ("Master the previous
  concepts to unlock — N of M assessment items to go" from `gate` of the
  first unmastered predecessor); soft mode renders the same panel as a
  dismissible warning above the (still visible) content; assessment inputs
  and discussion hidden in hard mode (server redacts anyway).
- **Path cards** (`kb/[kbId]/learn`): "N learners" badge from
  `learner_count`; gate-mode chip on the card when the mode isn't off.

## 7. Non-goals (later parts)

- `gate_override_after_days` valve (OQ-52) and per-concept thresholds
- Prerequisite-graph gating (no graph exists in the implemented model)
- Targeted review recommendations when a learner hits a gate (§4.4's
  remediation loop — needs retrieval work, separate design)
- Post editing, reactions, mentions, notifications, realtime (unchanged from
  docs/13 §7)

## 8. Verification plan (KC-091)

1. Unit: `compute_gates` matrix (mastered/locked transitions, threshold
   boundary at exactly the threshold, no-item concepts, pruned skipped,
   first concept open, all-mastered); PATCH validation; redaction shaping.
2. Live (Colima, two users same org): A publishes a multi-concept path, sets
   `hard` + threshold 1.0 → B's payload has concept 2 locked+redacted,
   attempt/learned/threads on it 422; B answers concept 1's items correctly
   → concept 2 unlocks (fresh GET); A flips to `soft` → content visible,
   nothing blocked; A flips to `off` → payload shape has `gate: null`;
   owner exemption (A sees everything under `hard`); non-owner PATCH 404;
   `learner_count` on the KB path list reflects B after activity.
3. Regression: default-off paths byte-identical (existing learn flows,
   attempt shape); full pytest; vue-tsc clean.
