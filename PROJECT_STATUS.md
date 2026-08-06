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
project_phase: "Active development — v0.8.0 released"
protogear_enabled: true
framework: "Vue 3 + Nuxt 3 (frontend) / Python 3.12 + FastAPI (backend)"
project_type: "Self-hosted web application"
initialization_date: "2026-06-01"
current_sprint: "v0.10.0 — Cohort learning, part 1 (in progress)"
last_release: "v0.9.0 (2026-08-06)"
ticket_prefix: "KC"
next_ticket: "KC-087"
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

## 🔄 v0.10.0: Cohort learning, part 1 (KC-080–086)

*Design in `docs/13-cohort-learning.md` (OQ-37–44), feature shape from `docs/03-learning-layer.md` §5.2/§5.4 — the roadmap's #1 V2 priority, first slice: persisted answer attempts (they are graded statelessly today — analytics cannot be backfilled), owner-only comprehension analytics, and passage-anchored discussion threads. "Cohort" = readers of the path (no new entity; reuses `get_readable_path`). Mastery gates deferred to part 2. Ships a pre-existing bug fix: `grade_attempt` never validated the item belongs to the path.*

### Sprint order (implement in sequence — 080 unblocks everything; 081 before 082)

- **KC-080** backend: Migration 017 — `assessment_attempts` (item/path/user FKs, answer_text, correct, soft matched_distractor_id), `discussion_threads` (concept FK, soft passage anchor + excerpt snapshot), `discussion_posts`; ORM models
- **KC-081** backend: persist attempts + scoping fix — concept-in-path validation (OQ-38, pre-existing cross-path grade leak), `AssessmentAttempt` row per attempt reusing the distractor match; response shape unchanged; unit tests
- **KC-082** backend: analytics — owner-only `GET /v1/learning-paths/{id}/analytics` (per-learner progress/attempts/correct-rate/last-activity + per-concept learned/correct-rate/top misconceptions); `concept_count` → non-pruned (OQ-43); pure aggregation helpers + tests
- **KC-083** backend: discussion API — thread/post create/list/get/delete guarded by `_get_readable_concept_id` (+ author-or-path-owner delete); passage anchor validated against the concept's source_passages, excerpt snapshotted; threads DESC, posts ASC (OQ-42); unit tests
- **KC-084** frontend: `ConceptDiscussion.vue` on the learn page — thread list with excerpt headers, thread view, anchored new-thread form, replies, delete; BFF handlers; vue-tsc clean
- **KC-085** frontend: owner-only Learners panel on the learn page — per-learner + per-concept tables from the analytics endpoint
- **KC-086** verification + release — doc §8 two-user live plan; changelog; release v0.10.0

## ✅ v0.9.0: Harness study KBs — self-teaching curriculum (KC-074–079)

*Design in `docs/12-harness-study-kb.md` (OQ-29–36): project a harness's slot contents, eval suite, and eval-run reports into a dedicated private KB so the existing curriculum flow can teach it. Prerequisite bug fix: the curriculum agent's heading heuristic is dead code (chunk text never contains `\n\n`), so every KB has always produced exactly one concept — KC-074 groups per source instead.*

### Sprint order (implement in sequence — 074 is the concept-count prerequisite; 075 unblocks 076/077)

- ~~**KC-074**~~ ✅ backend: curriculum grouping fix — `build_concept_groups` groups by source boundary + retained heading boundary + `MAX_GROUP_PASSAGES=8` cap; 5 unit tests with realistic (newline-free) chunker output — 142 total (2026-08-06)
- ~~**KC-075**~~ ✅ backend: Migration 016 — `harnesses.study_kb_id` (SET NULL) + `harness_study_docs` (UNIQUE kb/kind/ref); `HarnessStudyDoc` lives in models/asset.py so both manual import sites already cover it; applied live, head **016** (2026-08-06)
- ~~**KC-076**~~ ✅ backend: study-doc composition — pure `compose_slot_doc`/`compose_eval_suite_doc`/`compose_eval_run_doc` in `harnesses/study_docs.py`; 9 DB-free unit tests (2026-08-06)
- ~~**KC-077**~~ ✅ backend: study-KB service + router — `POST /v1/harnesses/{id}/study-kb` (owner-only 404, create-or-refresh via pure `plan_study_projection`, MinIO dual-write, commit-before-enqueue, 422 when nothing to study) + `GET` doc-status endpoint; `HarnessOut.study_kb_id`; 6 planner tests — 157 total (2026-08-06)
- ~~**KC-078**~~ ✅ frontend: Study KB panel on compose page — create/refresh button, 4s doc-status poll (board-summary idiom, resumed on mount), links to KB workspace + learn page; catch-all BFF covers the routes; vue-tsc clean (2026-08-06)
- ~~**KC-079**~~ ✅ verification + release — doc §8 live checks green on Colima (7-doc projection incl. FK-ordering fix found live, all embedded, idempotent re-POST `projected=0/skipped=7`, non-owner 404s, multi-concept learning path proving KC-074 + the feature together); changelog; release v0.9.0 (2026-08-06)

## ✅ v0.7.0: Teams, ACLs & org discovery (KC-065–070) — released 2026-08-06

*Design in `docs/10-teams-and-acls.md` (OQ-13–20): teams as ACL principals within an org (no new visibility value), one polymorphic `acl_grants` table (viewer/editor, KB/asset/harness — boards stay excluded per OQ-11), org-scoped explore tab, and JWT namespace claims **rejected** (OQ-13 reaffirms OQ-10 — SQL predicates keep join/leave/grant immediacy).*

- ~~**KC-065**~~ ✅ Migration 014 — `teams`/`team_memberships`/`acl_grants` + models + registration + org-leave/remove team-membership cascade; applied live, head **014** (2026-08-06)
- ~~**KC-066**~~ ✅ Teams API — `/v1/orgs/teams` CRUD + membership (creator auto-joins; creator/org-admin manage; same-org + duplicate-name guards); 4 guard unit tests (2026-08-06)
- ~~**KC-067**~~ ✅ ACL layer — `grant_subquery`/`readable_clause`/`editable_clause`/`has_grant` in predicates.py; all 7 read sites rewired; OQ-18 editor surface (KB add-source, asset versions, harness slots/eval); grants CRUD (POST upserts); granted KBs in dashboard list; eval-run reads for editors; 10 SQL-shape/guard tests — 129 total (2026-08-06)
- ~~**KC-068**~~ ✅ Org explore — `GET /v1/kbs/org` (PublicKBOut, no namespace leak) + `UserOut.org_name` + "My organisation" explore tab + `?tab=` deep links + `kbs/org` BFF (2026-08-06)
- ~~**KC-069**~~ ✅ Frontend sharing — Teams section on `/org` (create/expand/add/remove/delete); `ShareDialog` component on KB/asset/harness pages (user-by-handle or team, viewer/editor, permission switch, revoke); org-name team tooltips (2026-08-06)
- ~~**KC-070**~~ ✅ Live verification — 37-check three-user script (`scripts/verify-v070.sh`) all green: team guards, private-KB team grant reads (B 200 / C 404), cross-org user grant, editor writes on all three surfaces, revoke/team-removal/org-leave immediacy on unchanged tokens, org explore shape + auth, public regression; BFF chain verified (2026-08-06)

## ✅ v0.8.0: Cloud eval adapter (KC-071–073) — released 2026-08-06

*Design in `docs/11-cloud-eval-adapter.md` (OQ-21–28): Anthropic-only opt-in adapter behind `CLOUD_EVAL_ENABLED` + `ANTHROPIC_API_KEY` (default off = byte-identical behaviour, OQ-2 preserved); `eval_runs.provider` column instead of slug-encoding; case cap + token reporting + per-submission privacy confirm; per-case error handling/retries for local runs too.*

- ~~**KC-071**~~ ✅ Backend — Migration 015 (`eval_runs.provider`); settings (`CLOUD_EVAL_ENABLED` off by default, `ANTHROPIC_API_KEY`, `CLOUD_EVAL_MAX_CASES=25`, `CLOUD_EVAL_MAX_TOKENS=4096`); Anthropic SDK adapter with live Models API list + refusal handling; provider-aware `submit_eval` pre-flight (gate/model/cap 422s, 503 unreachable); worker provider dispatch, per-case error capture, local transient-error retry, token totals; `GET /v1/eval-models`; 8 unit tests — 137 total (2026-08-06)
- ~~**KC-072**~~ ✅ Frontend — `/api/models` BFF → `/v1/eval-models`; Local/Cloud optgroup selector ("provider::model" encoding, local-only default); per-submission cloud consent dialog naming what leaves the host; provider-aware error mapping incl. case-cap and not-enabled; provider chip + token usage on results; ERROR state in the case table (2026-08-06)
- ~~**KC-073**~~ ✅ Verification + release — disabled-path live checks green (eval-models shows only the Ollama group, forced `provider=anthropic` → 422 not-enabled, bogus provider → 422, migration 015 applied, local eval regression run completes through the new dispatch path); enabled-path (§8 step 2) requires an operator API key — runbook documented in the doc; release v0.8.0 (2026-08-06)

## ✅ v0.6.0: Organisations (KC-060–064) — released 2026-08-05

*Design accepted in `docs/09-organisations.md` (supersedes OQ-3): `team` visibility becomes same-organisation via `users.org_id` + a rotatable invite-code join flow; Default-org backfill preserves v0.5.x behaviour for existing users; no JWT changes.*

- ~~**KC-060**~~ ✅ organisations schema — Migration 013 (organisations table + `users.org_id/org_role` + Default-org backfill, oldest user = admin); `Organisation` model registered in both manual import sites; applied live, downgrade round-trip verified; migration head now **013** (2026-08-05)
- ~~**KC-061**~~ ✅ orgs domain — `/v1/orgs` create/me/join/leave/rotate-invite/member PATCH+DELETE; invite code admin-only in responses; `UserOut` gains `org_id`+`org_role`; 8 guard unit tests (112 total); all flows live-verified with a third user incl. 409/403/404/422 paths (2026-08-05)
- ~~**KC-062**~~ ✅ team read predicate — `team_or_public_clause` in organisations/predicates.py rewires all 7 access-check sites (+ filter branches scope automatically via the base predicate); 3 SQL-shape unit tests (115 total); live-verified same-org 200 / org-less 404 / join-leave immediate on unchanged token (2026-08-05)
- ~~**KC-063**~~ ✅ frontend — `/org` page (create/join forms when org-less; member list, leave, invite copy/rotate, promote/demote/remove for admins); BFF index.post + catch-all; sidebar user block links to `/org`; auth store User + team-badge tooltips on KB/asset/harness pages; vue-tsc clean; BFF chain verified live (2026-08-05)
- ~~**KC-064**~~ ✅ three-user live verification — full doc §9 script green: org-less registration, team KB/asset/harness reads (same-org 200 / outsider 404), shared-path view/attempt/note/learned by a same-org learner, join→immediate access→leave→immediate loss on unchanged tokens, rotate invalidating the old code, public + logged-out regression; found+fixed pre-existing MissingGreenlet in all public board listings (2026-08-05)

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

- 2026-08-06: v0.9.0 released — harness study KBs (Migration 016, owner-only create-or-refresh projection of slots/eval suite/runs into a private KB, compose-page Study KB panel) + the curriculum multi-concept fix (KC-074: heading heuristic was dead code, every path had exactly 1 concept; now groups per source); live-verified incl. a 7-concept path from a 7-doc study KB; 157 backend tests

- 2026-08-06: v0.8.0 released — cloud eval adapter (Migration 015 `eval_runs.provider`, opt-in Anthropic SDK adapter with live model list + refusal handling, guarded pre-flight incl. case cap, worker provider dispatch + per-case errors + token totals, grouped model selector + per-run consent dialog); disabled path live-verified byte-identical; 137 backend tests; Tier 4 complete

- 2026-08-06: v0.7.0 released — Teams (Migration 014, /v1/orgs/teams, org-leave cascade), per-resource ACL grants (viewer/editor on KB/asset/harness, 7 read sites + enumerated editor write surface, grants CRUD + ShareDialog), org-scoped explore ("My organisation" tab, /v1/kbs/org, org_name tooltips, ?tab= deep links); 37-check three-user live verification; 129 backend tests; JWT claims rejected as OQ-13

- 2026-08-06: Tier 4 designed — `docs/10-teams-and-acls.md` (teams, per-resource ACLs, org explore; JWT claims rejected as OQ-13) and `docs/11-cloud-eval-adapter.md` (opt-in Anthropic eval adapter); sprints v0.7.0 (KC-065–070) and v0.8.0 (KC-071–073) defined

- 2026-08-05: v0.6.0 released — Organisations (Migration 013 + backfill, /v1/orgs + /org page, org-scoped team visibility across KBs/paths/assets/harnesses); three-user live verification; pre-existing public-board-listing MissingGreenlet fixed; 115 backend tests

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
