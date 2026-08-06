# Harness Study KBs — Self-Teaching Curriculum (Tier 5, part 1)

> Status: **proposed** (2026-08-06). The last unshipped Tier 3 deferral:
> "Self-teaching curriculum from harness corpus (project harness + eval logs
> into KB → curriculum agent)". Proposed sprint: **v0.9.0 = KC-074–079**,
> after v0.8.0 (`docs/11-cloud-eval-adapter.md`).

## 1. Problem

The AI Assets pillar (Layer 4) and the Learning pillar (Layer 2) don't talk to
each other. A team that has iterated on a harness — prompt versions with
rationales, an eval suite, a history of eval runs with per-case failures —
has produced exactly the corpus a new teammate needs to get up to speed, but
that corpus is locked in asset tables. The learning machinery (ingestion →
chunks → curriculum agent → learning path with grounded assessment) already
exists and only needs Sources in a KB.

This design gives a harness a **study KB**: one click projects the harness's
slot contents, eval suite, and eval-run reports into a dedicated KB as
ingestable documents. From there the *existing* flows take over — Q&A against
the corpus, and "Generate learning path" on the KB's learn page.

## 2. Pre-existing defect this depends on (KC-074)

The curriculum agent's heading heuristic is dead code: `chunker.py`
`_split_sentences` splits on `\n` and `_build_windows` rejoins with a single
space, so **no chunk text ever contains `\n\n`** — `_extract_heading`
(`learning/agent.py:111`) always returns `None`, and `build_concept_groups`
puts *every chunk in the KB into one group*. Every learning path ever
generated has had exactly one concept, regardless of source count. (The
"1 concept per heading group" note in SESSION_HANDOFF's Known Limitations
described intent, not behaviour; the unit tests hand-build strings containing
`\n\n` that the chunker can never produce.)

A study KB with N facet documents would also collapse to 1 concept, so the
fix is a hard prerequisite — and it is a strict improvement for every
existing KB, making "more sources = more concepts" true for the first time.

## 3. Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-29 | Concept grouping fix | Group boundary = **new `source_id`** (chunks are already selected ordered by `(source_id, seq)`), plus the existing heading boundary within a source (kept — harmless today, correct if a future extractor emits headed chunks), plus a hard cap of `MAX_GROUP_PASSAGES = 8` non-overlap passages per group (a long source yields several concepts instead of one over-long prompt) | Cheapest lever that fixes the defect for all source types; keeps `build_concept_groups` pure and unit-testable with realistic (newline-free) chunker output. Context-bounds the per-group Ollama prompt on CPU hardware |
| OQ-30 | Harness ↔ KB link | Nullable `harnesses.study_kb_id` FK (`ON DELETE SET NULL`), Migration 016. One study KB per harness, lazily created on first projection | A join table implies many KBs per harness — not the product model. `SET NULL` means deleting the KB simply lets the next projection recreate it |
| OQ-31 | What gets projected | One Source per facet: each slot → its `AssetVersion` (role, title, version, model pin, rationale, full content); the eval suite → one cases document (input/expected/strategy per case); each **completed** eval run → one report document (model, provider, pass rate, per-case pass/fail with truncated outputs and errors), capped at the **10 most recent** completed runs | One-source-per-facet is what makes OQ-29's per-source grouping yield one concept per facet. Only completed runs have metrics worth teaching from; the cap bounds corpus growth on long-lived harnesses |
| OQ-32 | Source types | Slot docs: `prompt_asset` (existing type). Suite + run docs: `plain_text` (existing type) | Both types already flow through the pipeline's plain-text extractor and every frontend surface; no new enum value to audit |
| OQ-33 | Idempotency / refresh | New table `harness_study_docs (harness_id, kb_id, doc_kind 'slot'\|'eval_suite'\|'eval_run', ref_id, source_id)` with UNIQUE `(kb_id, doc_kind, ref_id)`; `ref_id` = `asset_version_id` for slot/suite docs, `eval_run_id` for run docs. `POST /study-kb` is create-or-refresh: ensure KB, insert + enqueue only docs not yet present, return `{kb_id, projected, skipped}` | Re-running after a slot swap or new eval runs adds only the new documents. Superseded slot versions stay in the corpus as history — that *is* the study material ("we moved from v2 to v3 because…"). `AssetSourceProjection` can't represent eval runs, so a dedicated table beats overloading it |
| OQ-34 | Authz + visibility | Projection is **harness-owner only** (strictest existing precedent: `AssetService.project_version`). The study KB is created **`private`** regardless of harness visibility; the owner can PATCH it open explicitly | Slots may reference asset versions the owner can read but that are `private` to someone else via grants; mirroring a `public` harness's visibility onto the study KB (the KC-058 board pattern) would republish that content. Private-by-default is leak-safe; opening it is a conscious act |
| OQ-35 | Curriculum trigger | None added — the study KB reuses the existing KB learn flow (`POST /v1/kbs/{id}/learning-paths`, 202 + 4s poll). The frontend panel links to the KB workspace and learn page once ingestion completes | The projection endpoint's job ends at "embedded sources exist". `create_stub`'s existing 422 (no indexed chunks) already guards early clicks; no new async machinery |
| OQ-36 | Durability + ordering | Projected content is dual-written to MinIO (`storage_key = raw/{user_id}/{source_id}/study-doc.md`) + Redis (same as `add_file_to_board`), and the DB **commits before** the `xadd` enqueue loop | Without `storage_key`, a worker retry after the 3600s Redis TTL is permanently unrecoverable (`pipeline.py` raises "Upload data expired"). Committing first removes the existing enqueue-before-commit race where the worker can see the job before the Source row |

## 4. Schema (Migration 016)

```
harnesses (add)
  study_kb_id  String(36) NULL REFERENCES knowledge_bases(id) ON DELETE SET NULL

harness_study_docs (new)
  id          String(36) PK
  harness_id  String(36) NOT NULL REFERENCES harnesses(id) ON DELETE CASCADE
  kb_id       String(36) NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE
  doc_kind    String(20) NOT NULL          -- slot | eval_suite | eval_run
  ref_id      String(36) NOT NULL          -- asset_version_id | eval_run_id
  source_id   String(36) NOT NULL REFERENCES sources(id)
  created_at  timestamptz NOT NULL
  UNIQUE (kb_id, doc_kind, ref_id)         -- uq_harness_study_docs_kb_kind_ref
```

`downgrade()` drops the table and the column.

## 5. Backend changes

- `learning/agent.py`: `build_concept_groups` gains source-boundary + group-size
  cap per OQ-29 (signature unchanged — chunks dicts already carry `source_id`).
- New `app/domains/harnesses/study_docs.py`: **pure** composition functions
  (`compose_slot_doc`, `compose_eval_suite_doc`, `compose_eval_run_doc`) —
  markdown-ish plain text in, string out; no DB, no I/O (test-suite constraint:
  no conftest/fixtures exist, all tests are pure-logic).
- `harnesses/service.py` (or a sibling `study.py` service): `ensure_study_kb`
  — resolve-or-create KB (`KnowledgeBaseService.create`, title
  `Study: {harness.title}`, visibility `private`, caller commits), stamp
  `study_kb_id`; `project_study_docs` — compute desired doc set (slots via
  `selectinload(HarnessAsset.asset_version)` + asset, suite cases via the
  `eval_suite` slot, last 10 completed runs), skip rows already in
  `harness_study_docs`, create Sources (`kb_id` stamped, per OQ-32 types),
  commit, then MinIO + Redis + `xadd` per new source (OQ-36).
- Router: `POST /v1/harnesses/{id}/study-kb` → 200 `{kb_id, projected, skipped}`
  (404 non-owner — same non-leak contract as eval runs; 422 if the harness has
  no slots and no completed runs — nothing to study);
  `GET /v1/harnesses/{id}/study-kb` → `{kb_id, docs: [{doc_kind, ref_id,
  source_id, ingestion_status}]}` for the frontend poll (404 if none yet).
- `HarnessOut` gains `study_kb_id`.

## 6. Frontend changes

- Compose page (`/harnesses/[id]/compose`): new **Study KB** section —
  "Create study KB" / "Refresh study KB" button; after POST, poll the GET
  endpoint every 4s (the board-summary idiom) until all docs reach
  `embedded`/`failed`; per-doc status list while ingesting; when ready, links
  to the KB workspace (`/kb/{id}`) and its learn page (`/kb/{id}/learn`).
- No new BFF file — the `server/api/harnesses/[...path].ts` catch-all covers
  both endpoints.

## 7. Non-goals

- Auto-generating the learning path after projection (OQ-35 — manual, existing flow)
- Deleting stale study docs on slot swap (history is a feature; a "rebuild from
  scratch" action can come later if corpora get noisy)
- Projecting queued/running/failed eval runs, or more than the 10 newest
- Editor-grant access to projection (owner-only until someone needs otherwise)
- Study KBs for boards/assets (the harness is where the practitioner story lives)

## 8. Verification plan (KC-079)

1. Unit: grouping fix with realistic chunker output (multi-source, no `\n\n`,
   overlap chunks skipped, cap splits); composition functions; service guards.
2. Live (Colima): build a harness with 2+ slots, seeded eval suite, ≥1 completed
   local eval run → POST study-kb → all docs reach `embedded` → generate
   learning path → **path has ≥2 concepts** (one per facet doc — proves both
   the feature and the KC-074 fix) → citations resolve to study-doc chunks.
   Re-POST → `projected=0`. Second user: 404 on POST/GET (non-owner).
3. Regression: existing KB learning-path generation still works (now multi-concept
   for multi-source KBs); 0 TypeScript errors; full pytest suite.
