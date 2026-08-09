# Synthesis Persistence & Board Projection — Design

> Status: **proposed** (2026-08-09). Follow-on to multi-source synthesis
> part 1 (`docs/16-multi-source-synthesis.md`) — a synthesis currently
> vanishes on navigation. This sprint makes results **saveable** (the
> author's record, like concept notes) and **projectable onto boards**
> (the sharing/curation path, mirroring KC-046's asset projection), and
> fixes the curation twin of the KC-095 enqueue-before-commit race.
> Proposed sprint: **v0.14.0 = KC-099–102**.

## 1. Problem

A comparison worth 2 CPU-minutes of generation evaporates on tab switch.
There is no way to keep it, re-read it, or share it — while the platform
already has both the "keep" primitive (author-owned rows, concept-note
precedent) and the "share" primitive (project a text artifact into a
board's dedicated KB as a typed Source, prompt-asset precedent, OQ-1).

## 2. Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-69 | Persistence entity | New `syntheses` table (Migration 019): `kb_id` FK CASCADE, `user_id` FK, `question`, `answer_text`, `citations` JSONB (the SSE citations dict, snapshot), `source_ids` JSONB, `created_at`. **Author-owned**: list/get/delete are author-only (404 non-leak) | A saved synthesis is the author's note on the KB — the concept-note privacy contract. Sharing goes through board projection, which is an explicit act. Citations are snapshotted because chunks are re-indexable (the passage-excerpt precedent, OQ-40) |
| OQ-70 | Save flow | Client submits the streamed result: `POST /v1/kbs/{kb_id}/syntheses` `{question, source_ids, answer_text, citations}`. Guards: readable KB 404; `check_source_selection` reuse (422); size caps (question ≤ 2k, answer ≤ 50k chars, ≤ 50 citations); citations shape validated by schema | The answer only exists client-side (it streamed there); server-side re-generation to "verify" would double a 2-minute CPU cost for no trust gain — the row is the author's own record, exactly like a note body |
| OQ-71 | Board projection | `POST /v1/boards/{board_id}/syntheses` `{synthesis_id, note?, lane?}` mirrors `add_asset_to_board`: composes a markdown doc, creates `Source(type="synthesis")` in the board's dedicated KB, enqueues ingestion; **idempotent re-add** reuses the Source via `synthesis_source_projections` UNIQUE(synthesis_id, kb_id) (Migration 019, the `asset_source_projections` twin). Board owner must be the synthesis author | `synthesis` joins the Source type enum for the same reason `prompt_asset` did (OQ-1): boards must distinguish projected artifacts from pasted text. Projection embeds the doc, so forks and board search inherit it |
| OQ-72 | Projected doc + storage | Pure `compose_synthesis_doc`: question as title, answer body, per-source appendix (source title + cited locators). Content dual-written to **MinIO** (`storage_key`) *and* the Redis upload cache | Dual-write is the KC-077 lesson — Redis-only content (the prompt-asset path's known gap) is unrecoverable after the 3600s TTL if the worker reclaims late. New projections shouldn't inherit a known failure mode |
| OQ-73 | Curation race fix | `add_source_to_board` / `add_file_to_board` / `add_asset_to_board` commit **before** XADD (and the new projection follows) | Same defect class as KC-095: the worker can consume the job, find no committed Source row, skip, and strand the item `pending`. Found by inspection while mirroring the pattern — fix it where it lives, not just in the new copy |
| OQ-74 | Surface | Compare tab: **Save** button once a stream completes; **Saved** list (question, date, expand → answer + citations, delete, **Add to board** board-picker). Board cards render the `synthesis` type icon | Everything stays on the page where synthesis happens; the board picker mirrors the asset-detail add-to-board dialog |

## 3. Schema (Migration 019)

```
syntheses (new)
  id           String(36) PK
  kb_id        String(36) NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE (indexed)
  user_id      String(36) NOT NULL REFERENCES users(id) (indexed)
  question     Text NOT NULL
  answer_text  Text NOT NULL
  citations    JSONB NOT NULL DEFAULT '[]'   -- list of {chunk_id, source_id, locator, excerpt}
  source_ids   JSONB NOT NULL DEFAULT '[]'
  created_at   timestamptz NOT NULL

synthesis_source_projections (new — asset_source_projections twin)
  id            String(36) PK
  synthesis_id  String(36) NOT NULL REFERENCES syntheses(id) ON DELETE CASCADE
  kb_id         String(36) NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE
  source_id     String(36) NOT NULL REFERENCES sources(id) ON DELETE CASCADE
  owner_user_id String(36) NOT NULL REFERENCES users(id)
  created_at    timestamptz NOT NULL
  UNIQUE (synthesis_id, kb_id)
```

`downgrade()` drops both.

## 4. Backend changes

- Models in `models/learning.py`? No — new `models/synthesis.py`, registered
  in both manual import sites (the KC-075 lesson).
- `generation/synthesis.py` grows `SynthesisStore` (or a sibling service):
  `save`, `list_for_kb` (author-only rows), `delete` (author-only);
  citation-shape schema `SavedCitation` (chunk_id/source_id/locator/excerpt).
- `curation/service.py`: `add_synthesis_to_board` mirroring
  `add_asset_to_board` (owner+author guard, compose doc, MinIO dual-write,
  commit-before-enqueue, IntegrityError → reuse Source); pure
  `compose_synthesis_doc` beside it or in the synthesis module.
- Race fix (OQ-73) in the three existing board-add paths.
- Routers: `POST/GET /v1/kbs/{kb_id}/syntheses`,
  `DELETE /v1/kbs/{kb_id}/syntheses/{id}`,
  `POST /v1/boards/{board_id}/syntheses`.
- Tests: save-payload validation, compose doc shape, projection guard
  decisions (pure parts).

## 5. Frontend changes

- Compare tab: Save button (posts the completed stream's state), Saved list
  with expand/delete/Add-to-board (board picker fetching own boards —
  asset-detail precedent); BFF handlers per learning-route convention.
- Board page: `synthesis` icon in the source-type map(s).

## 6. Non-goals

- Sharing saved syntheses directly (project to a board instead)
- Re-running a saved synthesis / freshness indicators
- Synthesis part 2 items (hop loops, cross-KB) — unchanged from docs/16 §6

## 7. Verification plan (KC-102)

1. Unit: payload caps/shape, compose doc, selection-guard reuse.
2. Live (Colima): run a synthesis → save → appears in list with citations;
   delete works; author-only 404 for a second user; project onto a board →
   `synthesis` Source embedded in the board KB, board card renders, re-add
   reuses the Source (no duplicate); board-KB search finds the answer text;
   race regression: two rapid board adds both leave `embedded` sources.
3. Regression: full pytest; vue-tsc; existing board add flows.
