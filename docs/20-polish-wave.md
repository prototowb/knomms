# Polish Wave — Part-2 Slices Across Three Layers (Design)

> Status: **proposed** (2026-08-12). Four independent items, each the
> highest-leverage "part 2" slice of a shipped feature: instructor
> prerequisite editing (docs/19 §6), discussion post editing (docs/13 §7),
> study-KB rebuild (v0.9.0 backlog), and the team-workspaces audit
> (V2 #4). Independent file footprints → implemented in parallel.
> Proposed sprint: **v0.17.0 = KC-111–115**.

## Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-88 | Prerequisite editing | `UpdateConceptRequest` gains `prerequisites: list \| None` on the existing owner-only concept PATCH. Validation (422): each entry `{concept_id, strength, rationale≤300}`; concept_id must be a **sibling** (same path, not self); strength ∈ required\|recommended; ≤3 entries; the **whole-path graph must stay acyclic** — pure `validate_edge_update(existing_by_id, concept_id, new_prereqs)` in gates.py (id-based twin of `sanitize_edges`, but *rejecting* instead of dropping: a human edit deserves an error, not silent repair) | The agent proposes, the instructor disposes — §3.3's override principle applied to edges. Reuses the concept PATCH (no new route family) |
| OQ-89 | Post editing | `PATCH /v1/learning-paths/{pid}/threads/{tid}/posts/{post_id}` — **author-only 403** (the path owner moderates by *deleting*, never by rewriting someone's words); body non-empty (422); Migration 021 adds `discussion_posts.edited_at` (NULL until first edit); `PostOut.edited_at`; UI shows "(edited)". Resolving via `get_thread` inherits the hard-mode gate (OQ-48) — consistent with create, unlike delete (OQ-50) | Moderation-by-rewrite is a trust violation; edited_at keeps the cohort honest about what changed |
| OQ-90 | Study-KB rebuild | `POST /v1/harnesses/{id}/study-kb` accepts `{"rebuild": true}`: deletes the study KB's `harness_study_docs` rows and their Sources (chunks cascade), then runs the existing create-or-refresh projection, which now re-projects everything. Owner-only as before; commit-before-enqueue preserved. Compose-page Rebuild button with confirm | The refresh path is additive by design (UNIQUE dedup) — a corrupted or noisy corpus needs a from-scratch escape hatch (flagged when v0.9.0 shipped) |
| OQ-91 | Team-workspaces audit | Read-only investigation → `docs/21-team-workspaces-audit.md`: what V2 #4 promises vs what orgs (v0.6.0) + teams/ACLs (v0.7.0) already deliver, and the true gaps (boards excluded from grants per OQ-11, owner-only authoring on shared KBs, etc.). No code | V2 #4 may already be ~done; audit before building is cheaper than building |

## Verification plan (KC-115)

1. Unit: `validate_edge_update` matrix (non-sibling, self, cycle against
   existing edges, cap, bad strength); post-edit guards.
2. Live: owner replaces a concept's prerequisites → learner gate flips
   accordingly; cycle edit → 422; non-sibling → 422; author edits a post →
   `edited_at` set, other user → 403, owner → 403 (moderates by delete
   only); study-KB rebuild → same doc set re-projected fresh (new Source
   ids, all embedded), idempotent refresh still works after.
3. Regression: full pytest; vue-tsc; v0.16.0 gate behaviour unchanged.
