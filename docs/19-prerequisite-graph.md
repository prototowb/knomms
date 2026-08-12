# Prerequisite Graph, Part 1 — Design (V2 roadmap #6)

> Status: **proposed** (2026-08-12). "Prerequisite graph inference — MVP:
> flat linear sequence" (`docs/06-roadmap.md`); spec shape in
> `docs/03-learning-layer.md` §3.4 (edges with strength + rationale, cycles
> rejected at write time) and §4.4 (graph-based gating). This part ships
> **agent-inferred prerequisite edges** and makes the v0.11.0 mastery gates
> **graph-aware**: independent branches unlock independently instead of
> being hostage to reading order. Editing edges, adaptive pacing, and
> testing-out stay in part 2. Proposed sprint: **v0.16.0 = KC-107–110**.

## 1. Problem

Since KC-074, multi-source KBs produce multi-concept paths — but the
concepts are ordered by source iteration order, not by dependency, and the
mastery gates (docs/14, OQ-47) lock strictly along that sequence. A path
built from three unrelated papers forces a learner to master paper 1's
concept before touching paper 3's, though nothing connects them. The spec
has always promised better: prerequisite *edges*, so gating follows actual
dependency and unrelated branches stay open.

## 2. Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-82 | Edge storage | `path_concepts.prerequisites` JSONB default `[]` (Migration 020): list of `{concept_id, strength, rationale}` — soft refs to **sibling** concepts in the same path; `strength ∈ required\|recommended` (§3.4) | Edges live and die with the path (concepts CASCADE); a JSONB list on the dependent concept keeps reads free (the path payload already ships concepts) and avoids an edges table for what is path-internal, read-mostly data. Pruned prerequisites are ignored at gate time, not deleted — everything about gates recomputes fresh |
| OQ-83 | Inference cost | **One** LLM call per path, after concept generation: numbered titles + explanation excerpts in, `[{from, to, strength, rationale}]` out ("from must be understood before to") | Pairwise checks (§6.2's sketch) are O(n²) generations — a 7-concept path would cost ~20 extra CPU-minutes. One structured pass captures the useful edges at 1/20th the cost; pairwise precision can come with GPU hardware |
| OQ-84 | Sanitization | Pure `sanitize_edges(n, raw)`: drop self-edges, out-of-range indexes, unknown strengths → `recommended`, duplicates (keep strongest), cap 3 prerequisites per concept; then add edges one by one, **dropping any edge that would close a cycle** (§3.4: cycles rejected at write time) | Model output is untrusted structure — the graph must be a DAG *by construction*, not by trust. Incremental cycle checks make the drop deterministic (model's own edge order = priority) |
| OQ-85 | Gate integration | Graph mode: a concept is locked iff any **required**, non-pruned prerequisite is unmastered; concepts with no required prerequisites are never locked; `recommended` edges never lock (UI hint only). A path with **zero** edges keeps the v0.11.0 sequence rule | Fail-open into the shipped behaviour: every pre-020 path (and any path where inference produced nothing) gates exactly as before. Independent branches opening immediately is the whole point of the graph |
| OQ-86 | Inference failure | Fail-open: bad JSON / timeout / zero valid edges leaves all `prerequisites` empty and the path generates normally | The edge pass is an enhancement pass — it must never be the reason a curriculum fails |
| OQ-87 | Surface | Concept header shows "Requires:" chips (click → jump to that concept; rationale as tooltip), dimmer "Recommended:" chips; the locked-panel unlock hint names the concept's own unmastered prerequisites instead of the linear predecessor | The graph is only trustworthy if the learner can see *why* something is locked and jump straight to the blocker |

## 3. Schema (Migration 020)

```
path_concepts (altered)
  prerequisites  JSONB NOT NULL DEFAULT '[]'
                 -- [{concept_id, strength: "required"|"recommended", rationale}]
```

`downgrade()` drops the column.

## 4. Backend changes

- `learning/agent.py`: `infer_prerequisites(titles_and_excerpts)` — one
  `_ollama_generate` call, `_parse_json_response` reuse, returns raw edge
  dicts (or `[]` on any failure, OQ-86).
- **New pure** `sanitize_edges(concept_count, raw_edges)` in
  `learning/gates.py` (it is gate-adjacent graph logic): OQ-84 rules,
  returns `{dependent_index: [{prereq_index, strength, rationale}]}`.
- `worker/curriculum.py`: after concepts flush (ids exist), run inference +
  sanitize, map indexes → concept ids, stamp `concept.prerequisites`.
- `learning/gates.py`: `compute_gates` gains graph mode (OQ-85) — concept
  dicts carry `prerequisites`; required-prereq locking with sequence
  fallback when the path has no edges.
- Schemas: `PathConceptOut.prerequisites: list[dict] = []`.
- Tests: sanitize matrix (self/range/dup/cap/cycle-break), graph-mode gates
  (independent branch open, required chain locks, recommended never locks,
  pruned prereq ignored, zero-edge fallback identical to v0.11.0).

## 5. Frontend changes

- Learn page: Requires/Recommended chips on the concept header (click
  navigates, tooltip shows rationale); `unlockHint` rewritten to name the
  concept's own unmastered required prerequisites in graph mode (linear
  fallback preserved); nav lock glyphs unchanged (server truth).

## 6. Non-goals (part 2 candidates)

- Instructor edge editing / adding / deleting (needs its own UX)
- Pairwise-precision inference, adaptive pacing, test-out flows (§4.4)
- Reorder warnings (no reordering UI exists)
- Cross-path or cross-KB prerequisite links

## 7. Verification plan (KC-110)

1. Unit: sanitize + graph-gate matrices per §4.
2. Live (Colima): regenerate a path on the multi-source verify KB → edges
   present and cycle-free with rationales; owner sets `hard` gates → a
   learner sees a no-prerequisite branch concept **unlocked** while the
   sequence rule would have locked it; mastering a required prerequisite
   unlocks its dependents (fresh GET); pre-existing path (no edges) gates
   exactly as v0.11.0; chips render with jump + tooltip.
3. Regression: full pytest; vue-tsc; attempt/learned flows unchanged.
