# PROJECT STATUS — Knowledge Comms

> **Single Source of Truth** for project state. Read this first every session.

## Hand-off — start here

**What this is.** A self-hosted, zero-external-cost grounded collective intelligence platform. Four pillars: AI knowledge core (RAG + agents), structured learning (AI-generated learning paths from corpora), discovery/curation (visual collection boards with fork-to-KB mechanic), and AI assets (prompt versioning, harness composition, local eval runs — the practitioner layer for teams building with AI). Full specification in `PROJECT_SPECIFICATIONS.md`.

**Where we are.** Active development — all five milestones complete, stack live on Colima. Three layers fully exercised end-to-end. See `SESSION_HANDOFF.md` for run instructions, live verification status, and what comes next.

**Read in this order:**

1. This file → current state and open tickets
2. `SESSION_HANDOFF.md` → run instructions, live verification, architectural invariants
3. `PROJECT_SPECIFICATIONS.md` → platform overview, tech stack, document map
4. `BRANCHING.md` / `TESTING.md` → conventions before any git or test work

**To run:**

```bash
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
docker compose up -d
# Frontend: http://localhost  API: http://localhost/api/v1  Swagger: http://localhost/api/docs
# Dev login: dev@localhost.dev / devdev99
```

---

## Current State

```yaml
project_phase: "Active development — v0.5.0 released"
protogear_enabled: true
framework: "Vue 3 + Nuxt 3 (frontend) / Python 3.12 + FastAPI (backend)"
project_type: "Self-hosted web application"
initialization_date: "2026-06-01"
current_sprint: "v0.5.1 — Sharing follow-ups (complete)"
last_release: "v0.5.1 (2026-08-04)"
ticket_prefix: "KC"
next_ticket: "KC-065"
```

## Architecture Summary

| Layer | Stack | Spec |
|---|---|---|
| Frontend | Vue 3 + Nuxt 3 + Tailwind + Pinia | `docs/07-frontend-architecture.md` |
| Backend API | Python 3.12 + FastAPI (modular monolith) | `docs/08-backend-architecture.md` |
| AI inference | Ollama + nomic-embed-text-v1.5 + LangGraph | `docs/02-ai-architecture.md` |
| Database | PostgreSQL 16 + pgvector | `docs/05-platform-architecture.md` |
| Storage | MinIO + Redis 7 + Redis Streams | `docs/05-platform-architecture.md` |
| Deployment | Docker Compose (single-host, zero external cost) | `docker-compose.yml` |

---

## 🔄 v0.6.0: Organisations (KC-060–064) — in progress

*Design accepted in `docs/09-organisations.md` (supersedes OQ-3): `team` visibility becomes same-organisation via `users.org_id` + a rotatable invite-code join flow; Default-org backfill preserves v0.5.x behaviour for existing users; no JWT changes.*

- ~~**KC-060**~~ ✅ organisations schema — Migration 013 (organisations table + `users.org_id/org_role` + Default-org backfill, oldest user = admin); `Organisation` model registered in both manual import sites; applied live, downgrade round-trip verified; migration head now **013** (2026-08-05)
- **KC-061** orgs domain — service + router at `/v1/orgs` (create/me/join/leave/rotate-invite/member PATCH+DELETE per doc §5), schemas, `UserOut` gains `org_id`+`org_role`; unit tests for service guards (last-admin, 409s)
- **KC-062** team read predicate — shared `team_or_public_clause` helper; rewire the 7 access-check sites (KB `get_readable_by_id`, learning `_readable_kb_exists`, harnesses ×3, assets ×2) + 2 `?visibility=team` filter branches; unit tests
- **KC-063** frontend — `/org` page (create/join/members/invite-code/admin controls) + BFF routes + dashboard link + team-badge tooltips
- **KC-064** three-user live verification (doc §9), docs sync, release v0.6.0

## ✅ v0.5.1: Sharing follow-ups (KC-058–059) — released 2026-08-04

*The two concrete leftovers from the v0.5.0 sharing sprint. The third idea (`organisations` table) stays Tier 3 — it re-opens OQ-3 and needs design first.*

- ~~**KC-058**~~ ✅ board-dedicated KB inherits board visibility — `create_board`/`fork_board`/`_resolve_board_kb` stamp the board's visibility on the KB they create; `PATCH /boards/{id}` visibility propagates via `BoardService.sync_board_kb_visibility`; live-verified both directions with a second user (public→200 on KB+sources, re-private→404) (2026-08-04)
- ~~**KC-059**~~ ✅ `POST /v1/sources` trailing-slash 307 — route now registered at both `""` and `"/"` (KB router convention), so neither form redirects through the nginx→Nuxt proxy chain; live-verified (422 on both forms, no 307). BFF was never affected — it calls the slashed path (2026-08-04)

## ✅ v0.5.0: Sharing layer (KC-053–057) — released 2026-08-04

*v0.4.0 shipped 2026-08-04. This sprint makes KBs shareable and everything that unblocks: shared learning paths with multi-learner progress, MC answer choices, metadata editing, and the deferred explore KBs tab. Design decisions: KB visibility uses the existing private|team|public enum (OQ-3: team = all instance users); the KB is the access boundary — `Source.visibility` stays dormant (documented, do not "fix"); reads relax, writes stay owner-only.*

### Sprint order (implement in sequence — 053 unblocks 054/057; 054 unblocks 055)

- ~~**KC-053**~~ ✅ KB visibility — Migration 012 `knowledge_bases.visibility` (+index); `get_readable_by_id` (new method; `get_by_id` stays the write guard); relax the 4 read sites (GET kb / sources / search, POST query) + drop the Source owner clause in the sources list; relax source-status poll to readable-KB; `KnowledgeBaseOut` gains `visibility` + `owner`; `PATCH /kbs/{id}` (boards precedent); create accepts visibility; frontend: `isOwner` gating on add-URL/upload, visibility badge
- ~~**KC-054**~~ ✅ shared learning paths — `get_readable_path` (owner OR published+readable-KB); split `_get_owned_concept_id` into readable (attempt/note/learned) vs owner (update/publish); add KB authz to the path-list endpoint (returns owner's paths + published for readers); `LearningPathOut`+Summary gain `owner`; frontend `isOwner` gates Publish/Accept/Prune. No schema change — progress/notes are already per-user
- ~~**KC-055**~~ ✅ MC answer choices — learner-facing `AssessmentItemLearnerOut` (omits `correct_answer` — fixes a pre-existing leak; adds server-shuffled `choices` seeded per item+user); owner keeps the full shape; frontend choice buttons submitting the choice *text* (grading unchanged); free-text fallback when an item has no distractors
- ~~**KC-056**~~ ✅ asset/harness metadata PATCH — `PATCH /assets/{id}` + `PATCH /harnesses/{id}` (title/description/visibility, boards PATCH shape, validation via service VISIBILITIES); edit controls on asset detail + harness compose (needs new `isOwner` there)
- ~~**KC-057**~~ ✅ KBs tab on explore — public-KB listing endpoint (`get_optional_user`); fourth explore tab; visibility badges on dashboard KB cards

### Known non-goals (documented, deliberate)

- ~~Board-dedicated KBs stay private even when the board is public~~ → shipped as KC-058 (v0.5.1)
- `Source.visibility` remains dormant; KB is the boundary
- Team members cannot author learning paths on shared KBs (create stays owner-only)

## ✅ v0.4.0: Learner layer + KB search (KC-047–052) — released 2026-08-04

*v0.3.0 shipped 2026-08-04. This sprint delivers the June backlog: private concept notes, learner progress, KB search, plus explore/auth polish. Notes: free-text MC input already shipped (f0fc1ed); "KBs tab on explore" deferred — it needs a `visibility` column + public listing endpoint (a pillar, not a ticket).*

### Sprint order (implement in sequence)

- ~~**KC-047**~~ ✅ backend+frontend: private concept notes — Migration 009 `concept_notes(user_id, concept_id UNIQUE, body)`; `GET/PUT /learning-paths/{pid}/concepts/{cid}/note`; private note card on the concept view
- ~~**KC-048**~~ ✅ backend+frontend: learner progress — Migration 010 `concept_progress(user_id, concept_id UNIQUE, learned_at)`; `POST/DELETE .../concepts/{cid}/learned`; `completion_pct` on `LearningPathSummary`; learner "Mark learned" toggle (distinct from the instructor ✓); scope: path owner only
- ~~**KC-049**~~ ✅ frontend: Assets tab on `/explore` — third tab against the existing public `GET /assets?q=` FTS
- ~~**KC-050**~~ ✅ frontend: auth-guard learning pages — `middleware: 'auth'` on `learn/[pathId]` and `kb/[kbId]/learn` (currently silent-fail when logged out)
- ~~**KC-051**~~ ✅ backend+frontend: KB semantic search — `GET /kbs/{kb_id}/search?q=` reusing `RetrievalService.retrieve`; result cards with Source title/type attribution; Search tab on the KB workspace
- ~~**KC-052**~~ ✅ backend: KB keyword search — Migration 011 GIN index on `chunks.text`; `mode=keyword|semantic` param on the search endpoint

### Deferred (design first, do not start)

- KBs tab on explore — requires `knowledge_bases.visibility`, public listing endpoint, privacy review
- Distractor rehabilitation — distractors are generated + stored but rendered nowhere since free-text input shipped; needs an answer-mode design decision

## ✅ v0.3.0: Tier 2 — AI Assets hardening + discovery (KC-030, KC-041–046)

*v0.2.0 shipped 2026-08-04. Tier 2: harden what shipped (eval grading tests, EvalCase API, UX fixes), then the deferred discovery features. Branching convention unchanged: feature branches from `development`, local merge, push `development`; PR to `main` for releases.*

### Sprint order (implement in sequence)

- ~~**KC-041**~~ ✅ backend: 18 unit tests for `worker/eval._normalize` + `_grade` — all 4 strategies, regex config/pattern fallback, unknown strategy → False; live-verified (2026-08-04)
- ~~**KC-042**~~ ✅ backend: EvalCase API — `GET /assets/{id}/versions/{num}/cases`; `POST /assets/{id}/versions` accepts `eval_cases[]` created atomically; 409 on dedup-with-cases; 422 validation (blank fields, unknown strategy, bad regex); live-verified (2026-08-04)
- ~~**KC-043**~~ ✅ frontend: eval case table per version + owner-only new-version composer (prefills content+cases from selected version); compose-page 0-case note links to the asset; live-verified via Playwright (2026-08-04)
- ~~**KC-044**~~ ✅ frontend: eval model default skips embedding models (`/embed/i` filter); live-verified (2026-08-04)
- ~~**KC-045**~~ ✅ fork-compare — `GET /harnesses/{id}/eval` run listing (owner-only); compose page Fork comparison section: pass-rate tiles, delta, per-case join when suite versions match; live-verified (2026-08-04)
- ~~**KC-046**~~ ✅ asset board curation — `POST /boards/{id}/assets` projects a version as a `prompt_asset` CollectionItem (idempotent re-add reuses the Source); Add-to-board modal on asset detail; live-verified incl. bugfix for MissingGreenlet in the re-add path (2026-08-04)
- ~~**KC-030**~~ ✅ async board summary — Migration 008 `summary_status`; `board.summary.jobs` stream + worker handler; 202/409/422; board page 4s poll; owner GET fix for private boards; live-verified (~25s generation on CPU) (2026-08-04)

## ✅ v0.2.0: AI Assets Pillar (KC-032–040) — released 2026-08-04

### Sprint order (implement in sequence — each ticket unblocks the next)

- ~~**KC-032**~~ ✅ schema: Migration 006 — 7 new tables live in Postgres; `prompt_asset` type; User back-populates (2026-06-05)
- ~~**KC-033**~~ ✅ backend: `AssetService` + router at `/api/v1/assets` — create, add version (SHA-256 dedup + auto-increment version_num), get, list, deprecate; 10 unit tests; code complete (2026-06-05)
- ~~**KC-034**~~ ✅ backend: `HarnessService` + router at `/api/v1/harnesses` — create, fork (copies HarnessAsset rows, increments fork_count, populates fork_lineage), get, list, add/swap asset version by role; code complete (2026-06-05)
- ~~**KC-035**~~ ✅ backend: eval worker — `eval.jobs` stream in `worker/__main__.py`; `worker/eval.py` grades EvalCase records (exact_match/contains/regex/llm_judge), writes EvalRun.metrics; 422 if model not local; SSE via Redis list polling; code complete (2026-06-05)
- ~~**KC-036**~~ ✅ backend: `AssetProjectionService.project` — creates `Source(type="prompt_asset")`, caches in Redis, pushes to ingestion.jobs, writes AssetSourceProjection; 409 on UNIQUE conflict; code complete (2026-06-05)
- ~~**KC-037**~~ ✅ frontend: asset library — `/assets` list page (type filter, visibility filter, debounced FTS search, create form); `/assets/[id]` detail page (version timeline, content block, rationale annotation, model-pin badge, status label, deprecate action); LCS-based version diff view; BFF catch-all routes for assets+harnesses; AI Assets nav link; syntax highlight deferred (Shiki not available) (2026-06-09)
- ~~**KC-038**~~ ✅ frontend: harness composer + eval — `/harnesses` list+create; `/harnesses/[id]/compose` slot manager (constrained role dropdown, add/swap modal, version meta from parallel asset fetch), eval panel (Ollama model selector, SSE progress, per-case table, 422/503 error distinction), fork dialog; `/api/models` BFF; Harnesses nav + explore tab (OQ-5); code complete (2026-06-10)
- ~~**KC-039**~~ ✅ frontend: drift alert + model-pin badge — `deprecated_models.json` (10 slugs); `GET /deprecated-models` endpoint; `ModelPinBadge` component (family chip + pin chip, deprecated=yellow); drift banner on asset detail + harness compose when any pin matches deprecated list (exact or family prefix); badge used in version timeline, content section, harness slot rows; code complete (2026-06-11)
- ~~**KC-040**~~ ✅ backend: asset full-text search — Migration 007: GIN indexes on assets+asset_versions; `GET /api/v1/assets?q=` with plainto_tsquery scoped to visibility; code complete (2026-06-05)

### Design decisions (resolved, do not re-open without cause)

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-1 | Source type for projected assets | `prompt_asset` added to enum | Boards need to distinguish projected prompts from pasted text |
| OQ-2 | Cloud-pinned model evals | Zero-external-cost strict; cloud adapter Tier 3 | Invariant is load-bearing for self-hosted value prop |
| OQ-3 | Team visibility scope | `team` = all registered users on this instance | No `organisations` table yet; document as known limitation. **Superseded by the organisations design (`docs/09-organisations.md`, OQ-6–12) — team = same org once v0.6.0 ships** |
| OQ-4 | EvalCase immutability | Adding cases requires a new AssetVersion commit | Aligns with versioning philosophy; eval suites are immutable per version |
| OQ-5 | Explore page surface | Tab on `/explore` (KBs \| Boards \| Harnesses) | Unified discovery; avoids top-nav proliferation |

### Deferred to Tier 2 (next sprint after KC-040)

- KC-030: Async board summary — defer until boards have multiple sources
- Harness fork-compare diff view (eval scores side-by-side vs. parent)
- Asset board curation (projected Sources as CollectionItems on boards)
- Asset library full-text search (KC-040 delivers this)

### Deferred to Tier 3 (future)

- Self-teaching curriculum from harness corpus (project harness + eval logs into KB → curriculum agent)
- Federation / selective public sharing with community quality signals
- Cloud model eval adapter (opt-in, with explicit cost + privacy guardrails)
- `organisations` table for true team-scoped visibility

## ✅ Post-MVP Sprint (KC-026–029)

- KC-029: MC answer grading — normalised exact-match (NFC + lower + collapsed whitespace + trimmed punctuation); fixes distractor feedback substring false-positives; 10 new tests (2026-06-02)

## ✅ Post-MVP Sprint (KC-026–028)

- KC-026: Async curriculum generation — POST returns 202, worker processes via `curriculum.jobs` stream (2026-06-02)
- KC-027: Curriculum worker rollback fix + board AI summary button — owner-only, ~21s on CPU (2026-06-02)
- KC-028: Similar boards — `GET /boards/{id}/similar` + "Similar boards" grid on board detail page (2026-06-02)

## ✅ MVP Launch Prep (NEXT items)

- NEXT-001: Integration run — all three layers exercised live on Colima (2026-06-02)
- NEXT-002: Source ingestion UI — URL paste + file upload in KB workspace (2026-06-01)
- NEXT-003: Board management UI — create board, add sources, swim-lane view (2026-06-01)
- NEXT-004: My Boards dashboard section (2026-06-02)
- NEXT-005: Public layout header — login/sign-up for unauthenticated visitors (2026-06-02)

## ✅ Milestone 3 Tickets

- KC-019: Migration 004 — extend collections + collection_items (board_embedding, layout_config, fork_count, lane) (2026-06-01)
- KC-020: BoardService — create, fork, get, list, add_source, search_semantic, curator_profile, summary (2026-06-01)
- KC-021: Board SSR page — swim-lane view, source cards, fork dialog (/board/[boardId]) (2026-06-01)
- KC-022: Fork action — dialog, new Collection + KB + source copy + ingestion queue (2026-06-01)
- KC-023: Curator profile page (/u/[handle]) — SSR, board grid (2026-06-01)
- KC-024: Semantic recommendation service — centroid nearest-neighbor via board_embedding (2026-06-01)
- KC-025: Explore page — live trending grid + semantic search (2026-06-01)

---

## ✅ Completed

- INIT-001: Proto Gear agent framework integrated (2026-06-01)
- SPEC-001: Platform vision and thesis — `docs/00-vision.md` (2026-06-01)
- SPEC-002: Product specification — personas, capabilities, journeys — `docs/01-product-spec.md` (2026-06-01)
- SPEC-003: AI architecture — ingestion, RAG, agents, guardrails — `docs/02-ai-architecture.md` (2026-06-01)
- SPEC-004: Learning layer — curriculum agent, data model, assessment — `docs/03-learning-layer.md` (2026-06-01)
- SPEC-005: Discovery layer — boards, fork mechanic, recommendations — `docs/04-discovery-layer.md` (2026-06-01)
- SPEC-006: Platform architecture — services, data models, auth, cost — `docs/05-platform-architecture.md` (2026-06-01)
- SPEC-007: Roadmap — MVP scope tables, milestones, hardware sizing — `docs/06-roadmap.md` (2026-06-01)
- SPEC-008: Frontend architecture — Vue 3/Nuxt 3, Tailwind, patterns — `docs/07-frontend-architecture.md` (2026-06-01)
- SPEC-009: Backend architecture — FastAPI, SQLAlchemy, worker, testing — `docs/08-backend-architecture.md` (2026-06-01)
- SPEC-010: Self-hosted architecture — Ollama, Docker Compose, zero-cost model (2026-06-01)
- SPEC-011: PROJECT_SPECIFICATIONS.md entry point (2026-06-01)

---

## ✅ Milestone 2 Tickets

- KC-013: Migration 003 — LearningPath, PathConcept, AssessmentItem, Distractor tables (2026-06-01)
- KC-014: Curriculum agent — heading-heuristic grouping + Ollama JSON generation (no LangGraph) (2026-06-01)
- KC-015: Assessment agent — MC questions with grounded distractors (embedded in curriculum agent) (2026-06-01)
- KC-016: Learning domain router — 6 endpoints for path CRUD, publish, concept review, MC grading (2026-06-01)
- KC-017: Frontend KB workspace — real Q&A UI with citation sidebar + learning path link (2026-06-01)
- KC-018: Frontend learning path views — path list, path detail with MC assessment + instructor controls (2026-06-01)

## ✅ Milestone 1 Tickets

- KC-007: Dockerfile + pyproject.toml fix (.[ingestion]); migration 002 (vector_namespace) (2026-06-01)
- KC-008: Ingestion domain — RawBlock, PDF/web extractors, chunker, service, router (2026-06-01)
- KC-009: Retrieval domain — pgvector cosine search, namespace-scoped, types module (2026-06-01)
- KC-010: Generation domain — Ollama client, citation injection/validation, SSE router (2026-06-01)
- KC-011: Worker — Redis Streams consumer, 7-stage ingestion pipeline, batched embed (2026-06-01)
- KC-012: Unit tests — 29/29 passing (chunker, citations, SSE format) (2026-06-01)

## ✅ Milestone 0 Tickets

- KC-001: Fix docker-compose.yml build paths and service contracts (2026-06-01)
- KC-002: .env.example, nginx/nginx.conf, backend/Dockerfile, frontend/Dockerfile (2026-06-01)
- KC-003: Backend skeleton — pyproject.toml, core modules, 5 ORM models (2026-06-01)
- KC-004: Alembic setup + baseline migration (pgvector extension + 5 tables) (2026-06-01)
- KC-005: Identity domain — /health + register/login/refresh/me endpoints (2026-06-01)
- KC-006: Nuxt 3 frontend scaffold — nuxt.config.ts, Tailwind, Pinia, auth store (2026-06-01)

---

## Recent Updates

- 2026-08-04: v0.5.1 released — sharing follow-ups (board-KB visibility sync, sources trailing-slash 307 fix); live-verified with a second user; `__pycache__` artifacts untracked

- 2026-08-04: v0.5.0 released — Sharing layer (KB visibility, shared learning paths, MC choices + answer-key leak fix, metadata PATCH, explore KBs tab); verified with a second user account; Migration 012

- 2026-08-04: v0.4.0 released — KC-047–052 (private notes, learner progress, explore assets tab, auth guards, KB semantic+keyword search) implemented and live-verified same day; migrations 009–011

- 2026-08-04: v0.3.0 released — KC-046 + KC-030 complete and live-verified (board curation, async summary); full Tier 2 sprint done in one day; 104 backend tests
- 2026-08-04: KC-041–045 complete and live-verified (104 backend tests; API + Playwright) — eval grading tests, EvalCase API, case viewer/composer UI, generation-model default, fork-compare view; KC-046 + KC-030 remain in v0.3.0
- 2026-08-04: v0.2.0 released — KC-035/038/039 live-verified on Colima (API + Playwright browser run); stale mid-sprint Docker images rebuilt; CHANGELOG updated; PR to main + tag v0.2.0
- 2026-06-11: KC-039 — drift alert + model-pin badge complete; all KC-032–040 done; v0.2.0 AI Assets Pillar feature-complete
- 2026-06-10: KC-038 — harness composer + eval UI complete; Harnesses nav + explore tab; next: KC-039 (drift alert + model-pin badge)
- 2026-06-09: KC-037 — asset library UI complete; migration 007 applied; BFF routes + list + detail + diff view; next: KC-038 (harness composer + eval UI)
- 2026-06-05: KC-033–036, KC-040 — all backend AI Assets tickets code complete; 79/79 tests pass; next: KC-037 (frontend asset library)
- 2026-06-05: KC-032 — Migration 006: 7 AI Assets tables (assets, asset_versions, harnesses, harness_assets, eval_cases, eval_runs, asset_source_projections); 69/69 tests pass
- 2026-06-05: v0.2.0 sprint prepared — AI Assets Pillar (KC-032–040); all design decisions resolved
- 2026-06-03: Git history rewritten — all commits now authored as `prototowb@gmail.com`; history force-pushed clean
- 2026-06-02: KC-029 — MC grading normalisation; v0.1.0 tagged and released (PR #4)
- 2026-06-02: KC-028 — similar boards recommendations via board_embedding centroid
- 2026-06-02: KC-027 — curriculum worker rollback fix; board AI summary button
- 2026-06-02: KC-026 — async curriculum generation via Redis Streams; GitHub remote configured
- 2026-06-01: Milestone 4 complete — auth flow, fork-KB fix, board embeddings, typecheck baseline
- 2026-06-01: Milestone 3 complete — discovery layer, boards, fork, explore, curator profiles
- 2026-06-01: Milestone 2 complete — curriculum agent, learning paths, MC assessment, frontend views
- 2026-06-01: Milestone 1 complete — ingestion loop, grounded Q&A, SSE streaming
- 2026-06-01: Milestone 0 complete — infrastructure baseline, Docker Compose, identity

---

*Maintained by Proto Gear Agent Framework*
