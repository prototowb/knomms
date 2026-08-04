# Changelog

All notable changes to Knowledge Comms are documented here.

---

## [0.4.0] — 2026-08-04

Learner layer + KB search (KC-047–052) — the June backlog, live-verified on Colima (API + Playwright) on release day.

### Features

#### Learning layer
- Private learner notes per concept — `GET/PUT /learning-paths/{pid}/concepts/{cid}/note`, unique per (user, concept), "My private note" card on the concept view (Migration 009)
- Learner progress — mark concepts learned (`POST/DELETE .../learned`, idempotent); "✓ Learned" pill distinct from the instructor Accept control; `completion_pct` (non-pruned denominator) and "% learned" on the path list (Migration 010)
- Learning pages now auth-guarded — logged-out visitors are redirected to login instead of silently failing

#### Knowledge core
- KB search — `GET /kbs/{kb_id}/search?q=&mode=semantic|keyword`: semantic reuses the namespace-scoped pgvector retrieval; keyword uses PostgreSQL FTS over chunks (GIN index, Migration 011); results carry source title/type attribution; Search tab with mode selector on the KB workspace

#### Discovery
- AI Assets tab on `/explore` — public-asset grid with FTS search; login hint for anonymous visitors

### Notes
- Free-text MC answer input was found already shipped (pre-v0.2.0) — stale docs corrected
- Deferred with rationale: KBs tab on explore (needs KB visibility schema), distractor rehabilitation (dead data since free-text input)

### Test Coverage
- 104 backend tests (pytest) · 0 TypeScript errors (vue-tsc)

---

## [0.3.0] — 2026-08-04

Tier 2 — AI Assets hardening + discovery integration (KC-030, KC-041–046). All features live-verified on Colima (API + Playwright) the same day.

### Features

#### AI Assets hardening
- Eval cases are API- and UI-manageable: `GET /assets/{id}/versions/{num}/cases`; `POST /assets/{id}/versions` accepts `eval_cases[]` committed atomically with the version (409 when content dedups to an existing version — cases stay immutable per version); 422 validation for blank fields, unknown strategies, and non-compiling regex patterns
- Asset detail: eval case table per version + owner-only "New version" composer that prefills content and cases from the selected version
- Harness fork comparison: `GET /harnesses/{id}/eval` run listing (owner-only); compose page shows latest fork vs. parent pass rates, delta, and a per-case PASS/FAIL join when both runs used the same eval suite version
- Eval model selector defaults to a generation model (embedding models excluded from the default pick)
- 18 unit tests for eval grading (`_normalize` + `_grade`, all four strategies)

#### Discovery integration
- Asset board curation: `POST /boards/{id}/assets` projects an asset version onto a board as a `prompt_asset` CollectionItem (lane + curator note, ingestion into the board's KB); re-adding an already-projected version reuses the existing Source; "Add to board" modal on asset detail
- Async board summary (KC-030): `POST /boards/{id}/generate-summary` returns 202 and enqueues `board.summary.jobs`; new `summary_status` column (Migration 008); board page polls every 4 s and resumes polling after reload; 409 while a run is in flight, 422 on empty boards
- `GET /boards/{id}` now returns the owner's own non-public boards when authenticated (fixes a pre-existing private-board 404)

### Infrastructure
- Server BFF routes use explicit `ofetch` — Nitro's typed-router `$fetch` overload hit TS "excessive stack depth" once the route count grew

### Test Coverage
- 104 backend tests (pytest) — +25 over v0.2.0
- 0 TypeScript errors (vue-tsc)

---

## [0.2.0] — 2026-08-04

AI Assets Pillar — the fourth platform layer: prompt/asset versioning, harness composition, and local eval runs for practitioner teams building with AI. All tickets KC-032–040. Live-verified end-to-end on Colima (API + browser) on 2026-08-04.

### Features

#### Layer 4 — AI Assets
- Asset library — versioned AI assets (`system_prompt`, `eval_suite`, `few_shot_set`, `chain_spec`, `tool_spec`) with SHA-256 content dedup, auto-incremented version numbers, rationale annotations, tags, and model pins (`/api/v1/assets`)
- Harness composition — role-based slots binding asset versions into a runnable configuration; constrained role vocabulary; add/swap version per role (`/api/v1/harnesses`)
- Harness fork — mirrors the board fork mechanic: copies slot rows, increments `fork_count`, records `fork_lineage`
- Local eval runs — `eval.jobs` Redis stream; worker grades `EvalCase` records via `exact_match` / `contains` / `regex` / `llm_judge` strategies; per-case latency + pass/fail persisted to `EvalRun.metrics`; run snapshots `eval_suite_version_id` for reproducibility
- Eval guardrails — 422 if the requested model is not local to Ollama (with available-model list), 503 if Ollama is unreachable; zero-external-cost invariant holds (no cloud fallback)
- Live eval progress — SSE stream (`/eval/{run_id}/events`) with per-case events; events replay for 1 h after completion
- Asset projection — project an asset version into a knowledge base as a `prompt_asset` Source via the ingestion pipeline
- Asset full-text search — PostgreSQL tsvector + GIN indexes, visibility-scoped (`GET /assets?q=`)
- Drift alert — `GET /deprecated-models` serves a curated slug list; yellow drift banner on asset detail and harness compose when any pinned model matches an entry exactly or by family; `ModelPinBadge` component (family + tag chips)
- Frontend — `/assets` library (filters, FTS search, create), `/assets/[id]` detail (version timeline, LCS diff view, deprecate action), `/harnesses` list + `/harnesses/[id]/compose` (slot manager, Ollama model selector, live eval panel with per-case table, fork dialog); Harnesses tab on `/explore`; AI Assets + Harnesses nav links

#### Platform
- Migration 006 — 7 new tables (assets, asset_versions, harnesses, harness_assets, eval_cases, eval_runs, asset_source_projections); `prompt_asset` Source type
- Migration 007 — GIN indexes for asset FTS
- BFF routes for assets, harnesses, models, and deprecated-models (Nuxt server routes → FastAPI)

### Test Coverage

- 79 backend tests (pytest) — +10 over v0.1.0 (asset service, harness service, projection)
- 0 TypeScript errors (vue-tsc)

### Known Limitations

- `EvalCase` records have no CRUD API — eval cases are seeded directly in Postgres per asset version (immutable per version by design; new cases require a new version)
- Drift detection is client-side only; the deprecated-model list is a curated JSON file baked into the API image
- Eval runs are Ollama-local only; cloud model adapter deferred to Tier 3
- `team` visibility means all registered users on the instance (no `organisations` table yet)
- The compose-page model selector defaults to the first Ollama model, which can be the embedding model (`nomic-embed-text`) — select a generation model explicitly

---

## [0.1.0] — 2026-06-02

First release. Three-layer platform fully operational on a self-hosted, zero-external-cost Docker Compose stack.

### Features

#### Layer 1 — AI Knowledge Core
- URL ingestion with chunking, embedding (nomic-embed-text-v1.5), and pgvector storage
- Grounded Q&A via SSE streaming with citation sidebar
- Namespace-scoped retrieval — each knowledge base is isolated

#### Layer 2 — Structured Learning
- Curriculum agent generates learning paths (heading-heuristic grouping + Ollama JSON generation)
- Multiple-choice assessment with grounded distractors and misconception feedback
- Accept/Prune/Publish instructor controls on learning path concepts
- Async curriculum generation — POST returns 202; worker processes via Redis Streams; frontend polls every 4 s
- MC answer grading uses normalised exact-match (NFC + lowercase + collapsed whitespace + trimmed punctuation), replacing fragile string comparison

#### Layer 3 — Discovery & Curation
- Visual collection boards with isolated KB per board
- Fork mechanic — new KB, new Source records, lineage tracked, full re-ingestion into fork namespace
- Board AI summary (owner-only, ~21 s on CPU, persists to `ai_summary`)
- Similar boards via pgvector cosine distance on stored board centroid embedding (`GET /boards/{id}/similar`)
- Explore page with semantic search and trending grid
- Curator profile pages (`/u/[handle]`)

#### Platform
- Auth — register / login / refresh / me with BFF pattern (Nuxt server routes → FastAPI)
- Docker Compose single-host deployment (Nginx → Nuxt BFF → FastAPI; Ollama; PostgreSQL 16 + pgvector; MinIO; Redis 7)
- Alembic migrations (005 revisions baseline through source `kb_id` backfill)
- Seed script (`scripts/seed-dev-user.sh`) — idempotent dev user creation
- Dashboard — My Knowledge Bases + My Boards preview sections
- Public layout with conditional auth header (login/sign-up vs dashboard/explore)

### Test Coverage

- 69 backend tests (pytest) — chunker, citations, learning agent, curation, MC grading normalisation
- 0 TypeScript errors (vue-tsc)

### Known Limitations

- Curriculum generates 1 concept per heading group; more sources → more concepts
- MC answer grading is radio-button only; free-text input not supported
- Board `generate-summary` is synchronous (~21 s); suitable for single-source boards
- `VISIBILITY_S=300` safe for single worker only — raise before scaling to multiple workers
- No session persistence across Colima restart (data volume persists; re-export `DOCKER_HOST`)

### Infrastructure Notes

- Colima (macOS) — always use `docker build --no-cache` to bypass layer-cache sync bug
- `RETRIEVAL_TOP_K=3` and `OLLAMA_READ_TIMEOUT=300` configurable in `.env` (GPU deployments: 10 / 60)
- All requests route through Nuxt (`nginx location /`) — BFF routes unreachable if bypassed
