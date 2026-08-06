# Changelog

All notable changes to Knowledge Comms are documented here.

---

## [0.9.0] — 2026-08-06

Harness study KBs (KC-074–079) — the AI Assets pillar and the Learning pillar finally talk to each other: one click projects a harness's prompt slots, eval suite, and recent eval-run reports into a dedicated private KB, and the existing curriculum flow turns that corpus into a learning path (design in `docs/12-harness-study-kb.md`, OQ-29–36). Ships with a foundational fix: **every learning path ever generated had exactly one concept** — the curriculum agent's heading heuristic was dead code, since chunker output never contains the `\n\n` it looked for.

### Fixed

- Curriculum concept grouping (KC-074): groups now split on source boundaries (plus retained heading boundaries and an 8-passage cap), so multi-source KBs produce multi-concept learning paths for the first time — "more sources = more concepts" is now actually true

### Features

#### Harness study KBs
- `POST /v1/harnesses/{id}/study-kb` (owner only): create-or-refresh projection — one Source per facet (each slot's asset version with rationale and model pin, the eval suite's cases, the 10 most recent completed eval runs with per-case failures), so each facet becomes its own concept
- Refresh is idempotent: re-running after a slot swap or new eval runs projects only what's missing; docs whose ingestion failed are re-queued
- The study KB is always created **private** (a public harness's slots may carry content shared with the owner via grants — mirroring visibility would republish it); the owner can open it explicitly
- Projected docs are dual-written to MinIO, so worker retries survive the Redis upload TTL; DB commits before jobs are enqueued
- `GET /v1/harnesses/{id}/study-kb`: per-doc ingestion status; `HarnessOut` gains `study_kb_id`; `harnesses.study_kb_id` + `harness_study_docs` (Migration 016)
- Compose page grows an owner-only **Study KB** panel: create/refresh, per-doc status table with 4s poll, links to the KB workspace and its learn page once everything is embedded

### Test Coverage
- 157 backend tests (pytest) · 0 TypeScript errors (vue-tsc) · migration head 016

---

## [0.8.0] — 2026-08-06

Cloud eval adapter (KC-071–073) — the last Tier 4 candidate and the guarded exception OQ-2 always promised: eval runs (and only eval runs) can target Anthropic models, strictly opt-in (design in `docs/11-cloud-eval-adapter.md`, OQ-21–28). **Default behaviour is byte-identical to v0.7.0** — with no configuration, no cloud code path is reachable and no request leaves the host.

### Features

#### Cloud eval adapter (opt-in)
- Operator opt-in via `CLOUD_EVAL_ENABLED=true` + `ANTHROPIC_API_KEY`; both required, default off
- `eval_runs.provider` column (Migration 015) — `model_pin` stays a bare model id, no slug encoding
- Official Anthropic SDK adapter: live model list from the provider's Models API (no hardcoded ids), safety-refusal handling, SDK retry with backoff on 429/5xx
- Provider-aware pre-flight in `POST /harnesses/{id}/eval`: opt-in gate, live model validation, and a case-count cap (`CLOUD_EVAL_MAX_CASES`, default 25) refused **before** any spend
- Per-case token usage recorded and totalled in run metrics; shown with the result
- `GET /v1/eval-models`: eval targets grouped by provider; the compose page selector shows Local/Cloud optgroups (cloud never a silent default) and asks for explicit consent on every cloud submission — the dialog names what leaves the host
- Reliability for all providers: a failed case no longer fails the whole run (error captured per case, shown as ERROR in the case table), and transient local Ollama errors retry with backoff

### Test Coverage
- 137 backend tests (pytest) · 0 TypeScript errors (vue-tsc) · migration head 015

---

## [0.7.0] — 2026-08-06

Teams, ACLs & org discovery (KC-065–070) — sharing gets a scalpel: named teams inside an organisation, per-resource viewer/editor grants on KBs/assets/harnesses, and an explore tab for what your org has shared (design in `docs/10-teams-and-acls.md`, OQ-13–20). Live-verified with a 37-check three-user script. JWT namespace claims were assessed and **rejected** (OQ-13): SQL-predicate enforcement keeps join/leave/grant changes instant on unchanged tokens.

### Features

#### Teams within organisations
- `teams` + `team_memberships` tables (Migration 014); any org member creates a team (auto-joining it), creator + org admins manage it; members must belong to the same org
- `/v1/orgs/teams` API: create/list/get/rename/delete + member add/remove (self-removal allowed); deleting a team revokes its grants
- Leaving or being removed from an org purges the user's team memberships — team-derived access cannot outlive org membership
- `/org` page grows a Teams section: create, expand to member roster, add/remove members, delete

#### Per-resource ACL grants
- One polymorphic `acl_grants` table: viewer/editor grants to a user (by exact handle, cross-org allowed) or a team (own org only) on a KB, asset, or harness; editor implies viewer; POST upserts the permission
- Reads: one shared `readable_clause` layers grants onto the v0.6.0 visibility predicate at all 7 read sites — KB grants flow transitively to sources, search, Q&A, and shared learning paths
- Writes (the enumerated editor surface): KB add-source (URL + upload), asset version commits, harness slot add/swap + eval submission; eval-run reads relax to editors so they can watch runs they trigger. Visibility, metadata, deprecation, and grant management stay owner-only
- Grants CRUD at `/v1/{kbs,assets,harnesses}/{id}/grants` (owner only); granted KBs appear in the grantee's dashboard list; granted assets/harnesses already surface via their list predicates
- Share dialog on KB workspace, asset detail, and harness compose: grant list with permission switch + revoke, share-to-user or share-to-team

#### Org-scoped explore
- "My organisation" explore tab (org members only): team-visible KBs (`GET /v1/kbs/org`), assets, and harnesses shared within the org; private granted items deliberately excluded
- Explore tabs are now deep-linkable (`/explore?tab=…`)
- `/auth/me` gains `org_name`; team badges finally say "Team — visible to <org name>"

### Test Coverage
- 129 backend tests (pytest) · 0 TypeScript errors (vue-tsc) · migration head 014

---

## [0.6.0] — 2026-08-05

Organisations (KC-060–064) — `team` visibility finally means something: same organisation, not "everyone on the instance" (supersedes OQ-3; design in `docs/09-organisations.md`). Live-verified with a three-user script (two org members + an org-less outsider).

### Features

#### Organisations
- `organisations` table + nullable `users.org_id`/`org_role` (Migration 013); single optional org per user — teams-within-orgs and ACLs stay Tier 4
- Upgrade backfill: all pre-existing users land in a "Default organisation" (oldest user as admin) so nothing previously readable breaks; fresh installs skip it and new users register org-less
- `/v1/orgs` API: create (caller becomes admin), join by rotatable invite code, leave (last-admin guard), member promote/demote/remove (last-admin + remove-self guards); invite code visible to admins only
- `/org` page: create/join forms when org-less; member list, leave, invite copy/rotate and role controls for admins; sidebar user block links to it

#### Team visibility semantics
- Every team/public read check now goes through one shared predicate: public is open to all, team requires owner and reader to share a non-NULL org (org-less readers get public only). Applies to KBs (workspace, sources, search, Q&A, status poll), shared learning paths, assets, harnesses, and the `?visibility=team` list filters
- Enforcement is per-request SQL — no JWT changes, so joining or leaving an org changes access immediately on an unchanged token
- Boards keep their deliberate public/private-only surface; a team badge tooltip now explains org scope on KB/asset/harness pages

### Fixes
- Public board listings (trending, semantic search, similar boards, curator profile) 500'd with MissingGreenlet once any public board reached the 3-item quality floor — summary queries now eager-load `items` + `owner` (pre-existing, caught during release verification)

### Test Coverage
- 115 backend tests (pytest) · 0 TypeScript errors (vue-tsc) · migration head 013

---

## [0.5.1] — 2026-08-04

Sharing follow-ups (KC-058–059) — the two concrete leftovers from v0.5.0's known-limitations list, live-verified on Colima with a second user account.

### Features
- Board-dedicated KBs now inherit their board's visibility (KC-058): all three KB-creation sites stamp the board's visibility, and `PATCH /boards/{id}` visibility changes propagate to the linked KB in both directions (public→readers gain KB/source/search access; private→404 again)

### Fixes
- `POST /v1/sources` without a trailing slash no longer 307-redirects through the proxy chain (KC-059) — the route is registered at both path forms, matching the KB router convention
- Untracked 13 committed `__pycache__` artifacts that produced spurious diffs on every test run

### Test Coverage
- 104 backend tests (pytest) · 0 TypeScript errors (vue-tsc)

---

## [0.5.0] — 2026-08-04

Sharing layer (KC-053–057) — knowledge bases become shareable and everything downstream unblocks. Live-verified on Colima with a second user account (cross-user reads, write denials, learner shapes).

### Features

#### KB sharing
- `knowledge_bases.visibility` (private|team|public, Migration 012); team = all registered users per OQ-3
- Reads relaxed for readable KBs: workspace, source list, semantic/keyword search, grounded Q&A, source-status polling; writes (ingest, upload, asset projection, path creation) stay owner-only
- `PATCH /kbs/{id}` (title/visibility); create accepts visibility; `KnowledgeBaseOut` carries `visibility` + `owner`
- Workspace: owner-clickable visibility badge (cycles private→team→public); add-URL/upload hidden for readers; owner attribution shown

#### Shared learning paths
- Published paths on readable KBs are usable by any registered user: view, attempt, private notes, mark-learned — all per-user (no schema change needed); Accept/Prune/Publish stay owner-only
- Path list endpoint gains KB authz (previously returned 200 `[]` with no check); readers see published paths with owner attribution

#### Assessment
- Multiple-choice answers: server-built `choices` (correct + distractors, deterministic per-user shuffle, opaque ids); choice buttons submit the choice text so grading is unchanged; free-text remains for choice-less items
- **Security fix:** learner responses no longer include `correct_answer` or the distractor list — both shipped the answer key to every client since M2

#### Metadata editing
- `PATCH /assets/{id}` and `PATCH /harnesses/{id}` (title/description/visibility, owner-only); clickable visibility badges on asset detail and harness compose

#### Explore
- Knowledge Bases tab: public-KB grid (unauthenticated), `GET /kbs/public` omits internal fields; dashboard KB cards show team/public badges

### Known limitations
- Board-dedicated KBs remain private even when their board is public
- `POST /v1/sources` (no trailing slash) 307-redirects through the proxy chain — use `/v1/sources/` for direct API calls (BFF routes unaffected; pre-existing)

### Test Coverage
- 104 backend tests (pytest) · 0 TypeScript errors (vue-tsc)

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
