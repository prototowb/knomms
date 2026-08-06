# Session Handoff — Knowledge Comms

**Session date:** 2026-08-06  
**State:** v0.7.0 released — Teams, ACLs & org discovery shipped (KC-065–070); everything KC-032–070 live-verified  
**Branch:** `development` ahead of `main` pending release PR / in sync once v0.7.0 PR merges  
**Tests:** 129/129 backend (pytest) · 0 TypeScript errors (vue-tsc)  
**Live verification:** everything through KC-070 verified on Colima (37-check three-user script, `scripts/verify-v070.sh`, 2026-08-06). Migration head: **014**.  
**Stack:** Running on Colima (macOS) — see §Dev Runtime

**v0.7.0 (2026-08-06):** teams + per-resource ACL grants + org explore (`docs/10-teams-and-acls.md`, OQ-13–20). The predicate family in `organisations/predicates.py` grew: `readable_clause(model, resource_type, user)` is now the only correct read relaxation (it layers `acl_grants` onto `team_or_public_clause`) and `editable_clause`/`has_grant(…, permissions=("editor",))` guard the enumerated editor write surface — never hand-roll grant subqueries. JWT claims were **rejected** (OQ-13), not deferred: enforcement stays per-request SQL so grant/membership changes are instant on unchanged tokens. Gotchas: `get_team` needs `populate_existing=True` (membership rows are inserted by FK, not relationship, so the loaded collection goes stale); the literal `/kbs/org` route must stay registered before `/kbs/{kb_id}`; the `kbs/` BFF dir has no catch-all — KB grants got hand-written ofetch routes. Next Tier 4 item queued: **v0.8.0 cloud eval adapter** (`docs/11-cloud-eval-adapter.md`, KC-071–073, not started).

**v0.6.0 (2026-08-05):** `team` visibility now means *same organisation* (`docs/09-organisations.md`, supersedes OQ-3). Migration 013 backfilled both dev users into "Default organisation" (dev@localhost.dev is admin). Org management at `/org`; API at `/v1/orgs`. The shared `team_or_public_clause` (organisations/predicates.py) is now the only correct way to write a team/public read check — never hand-roll `visibility.in_(("team","public"))` again. Found+fixed during verification: all public board listings 500'd (MissingGreenlet) once a public board hit the 3-item quality floor — board-summary queries must eager-load `items` + `owner`.

> **Local test/typecheck note (2026-08-04):** no repo venv — backend tests run with pyenv's `python3.13 -m pytest tests/ -q` (system `python3` lacks the deps). `pg ticket create` silently writes nothing (prints ✓KC-001, no file change) — manage tickets by editing PROJECT_STATUS.md directly, as every prior session did.

## Session 2026-08-04 — summary

Four releases in one day, each fully live-verified before tagging:

| Release | Sprint | Tickets | Highlights |
|---|---|---|---|
| v0.2.0 | AI Assets Pillar | KC-032–040 | Released after live-verifying the 3 code-complete tickets; root-caused stale mid-sprint images |
| v0.3.0 | Tier 2 hardening | KC-030, KC-041–046 | EvalCase API + UI, fork-compare, board curation, async board summary; 1 bug found+fixed in verification |
| v0.4.0 | Learner layer + KB search | KC-047–052 | Private notes, learner progress, semantic+keyword KB search, explore assets tab |
| v0.5.0 | Sharing layer | KC-053–057 | KB visibility, shared paths, MC choices + answer-key leak fix, metadata PATCH, explore KBs tab; verified with a second user |
| v0.5.1 | Sharing follow-ups | KC-058–059 | Board-KB visibility sync (both directions, incl. PATCH propagation), sources trailing-slash 307 fix; `__pycache__` untracked |

Migrations 008→012 applied. Backend tests 79→104. Two pre-existing security/correctness issues fixed along the way (private-board owner 404, assessment answer-key leak). Gotchas learned are recorded in §What Comes Next.

> ⚠ **Stale-image lesson (2026-08-04):** the stack had been running images built mid-sprint — `/v1/deprecated-models` 404'd and the models BFF served HTML until api/worker/frontend were rebuilt with `docker build --no-cache` per §Architectural Invariants. After any release, rebuild all three images before verifying.

---

## How to Re-orient

```bash
# 1. Start the stack (if not running)
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
docker compose up -d

# 2. Run models if not loaded
docker compose run --rm ollama-init

# 3. Verify (note: there is no /api/health BFF route — FastAPI /health is internal;
# check via Swagger or an authenticated endpoint instead)
curl -s http://localhost/api/models        # {"models":[...]} proves nginx→Nuxt→FastAPI→Ollama chain
cd backend && python3 -m pytest tests/ -q  # 104 passed
cd frontend && npx vue-tsc --noEmit -p tsconfig.json  # clean

# 4. Log in
# email: dev@localhost.dev  password: devdev99  (or test@example.com / password123)
```

---

## Git / GitHub Setup

- **Remote:** `https://github.com/prototowb/knomms.git` (added as `origin`)
- **Local identity:** `Tobias Rauer <prototowb@gmail.com>` (set via `git config user.*` in this repo)
- **Auth:** `gh` CLI installed (`brew install gh`), authenticated as `prototowb` — runs `gh auth setup-git` to wire HTTPS credentials
- **Branching convention:** `feature/KC-XXX-description` from `development` → merge locally → push `development` → PR `development` → `main` for releases. Feature branches stay local only.
- **State:** `main` and `development` both at the same commit — no pending PRs

---

## Dev Runtime (Colima / macOS)

Docker is NOT installed natively — use **Colima**:

```bash
colima start --cpu 4 --memory 8 --disk 60   # first time only
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
# Add to ~/.zshrc to persist:
# export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
```

**Critical: `docker compose build` vs `docker build`**

`docker compose build` uses a layer cache that does NOT invalidate when source files change (a Colima filesystem sync bug). Always use direct `docker build` for final images:

```bash
# CORRECT — bypasses stale cache
docker build --no-cache -t knomms-api:latest ./backend
docker build --no-cache -t knomms-frontend:latest ./frontend
docker compose up --force-recreate -d api frontend

# WRONG — may ship stale code silently
docker compose build api
```

---

## Live Verification Status

| Layer | Feature | Status | Notes |
|---|---|---|---|
| Layer 1 (Core) | Ingest URL | ✓ | ~2min for Wikipedia; UA header required |
| Layer 1 (Core) | Grounded Q&A SSE | ✓ | ~130s on CPU (top_k=3); citations sidebar works |
| Layer 2 (Learning) | Curriculum agent | ✓ | ~3:37 on CPU per path; 1 concept for 1-source KB |
| Layer 2 (Learning) | Learning path UI | ✓ | Accept/Prune/Publish controls; MC assessment |
| Layer 3 (Discovery) | Board create | ✓ | Creates isolated KB + collection join row |
| Layer 3 (Discovery) | Add URL to board | ✓ | Ingests to board's dedicated KB |
| Layer 3 (Discovery) | Fork board | ✓ | New KB + new Source records + lineage; ingests to fork namespace |
| Auth | Register/login/me | ✓ | BFF routes through Nuxt; token → fetchMe → isLoggedIn |
| UX | Seed script | ✓ | `scripts/seed-dev-user.sh` — idempotent, treats 409 as success |
| UX | Dashboard boards | ✓ | My Boards preview (up to 3) below KBs; See all → /boards |
| UX | Public header auth | ✓ | Login/Sign up (logged out) · Dashboard/Explore (logged in); ClientOnly avoids SSR mismatch |
| Layer 2 (Learning) | Async curriculum gen | ✓ | POST returns 202 with `status=generating`; worker flips to `draft`; frontend polls every 4s |
| Layer 3 (Discovery) | Board AI summary | ✓ | Owner-only button on board detail page; ~21s on CPU (metadata-only prompt); persists to `ai_summary` |
| Layer 3 (Discovery) | Similar boards | ✓ | `GET /boards/{id}/similar` — pure pgvector cosine distance on stored centroid; grid on board detail page |
| Layer 2 (Learning) | MC answer submit | ✓ | Radio-button choices; endpoint returns correct/incorrect + correct answer text; verified via API |
| Layer 2 (Learning) | MC grading normalisation | ✓ | NFC + lower + collapse whitespace + trim punctuation; distractor feedback uses same normaliser (KC-029) |
| Layer 4 (AI Assets) | AssetService CRUD | ✓ | KC-033 — POST/GET/list/deprecate at /api/v1/assets |
| Layer 4 (AI Assets) | HarnessService CRUD | ✓ | KC-034 — create/fork/get/list/add-slot/swap-slot at /api/v1/harnesses |
| Layer 4 (AI Assets) | Eval worker | ✓ | KC-035 — verified 2026-08-04: 0-case run completes (0/0), 4-case run 3/4 with all 3 non-judge strategies graded correctly, SSE events stream incrementally, 422 on missing model (+list), 503 with Ollama down, `failed` status when no `eval_suite` slot, `eval_suite_version_id` snapshot correct |
| Layer 4 (AI Assets) | Asset projection | ✓ | KC-036 — POST /assets/{id}/versions/{num}/project → prompt_asset Source → ingestion.jobs |
| Layer 4 (AI Assets) | Asset FTS | ✓ | KC-040 — GET /assets?q= with tsvector GIN; Migration 007 applied |
| Layer 4 (AI Assets) | Asset library UI | ✓ | KC-037 — /assets list + /assets/[id] detail + diff view; BFF routes; nav link |
| Layer 4 (AI Assets) | Harness composer + eval | ✓ | KC-038 — verified 2026-08-04 via Playwright: list+create, empty state, constrained role dropdown (5 roles), add/swap slot (role locked in swap), model selector, live progress + per-case table (75% warning tile), fork dialog preserves slots + identical fork eval pass rate + fork_count increment |
| Layer 4 (AI Assets) | Drift alert + model-pin badge | ✓ | KC-039 — verified 2026-08-04 via Playwright: family match (`llama2:7b`) and exact-entry match (`mistral:7b-instruct-v0.2`) both banner on asset detail + compose; clean pin (`mistral:7b-instruct`) does not; deprecated version *status* does not trigger the drift banner (separate concept) |

---

## CPU Performance Reality (4 cores, 8GB, no GPU)

| Operation | Time | Notes |
|---|---|---|
| URL ingest (embedding only) | ~1-3 min | httpx fetch + chunk + embed with nomic-embed-text |
| Q&A (top_k=3) | ~130s | 120s CPU prefill + 8s generation (84 tokens) |
| Curriculum generation | ~3:37 | 1 concept, sequential Ollama calls |
| Ollama "hello" (tiny prompt) | <1s | Fast for short context; prefill is the bottleneck |

`RETRIEVAL_TOP_K` and `OLLAMA_READ_TIMEOUT` are configurable in `.env`. Default: 3 and 300s (CPU). GPU deployments: set 10 and 60.

---

## Architecture Note: Nginx → Nuxt BFF

After verification the nginx config was changed: all requests go to Nuxt first (`location /` → Nuxt), not to FastAPI directly. The Nuxt server routes act as the BFF:
- `/api/auth/*`, `/api/kbs/*`, `/api/boards/*`, etc. → Nuxt BFF → FastAPI
- `/api/v1/*` → `server/api/v1/[...path].ts` catch-all → FastAPI (for curl/Swagger)
- `/api/docs`, `/api/openapi.json` → FastAPI directly (specific nginx rules)

This was the root cause of the auth 404 at first run: old nginx routed `/api/` → FastAPI, bypassing all BFF routes entirely.

---

## Runtime Bugs Fixed This Session (12 total)

Beyond the 6 static bugs (see previous handoff entries), the following were found during live testing:

| Bug | Symptom | Fix |
|---|---|---|
| bcrypt>=4 breaks passlib | register 500 | `bcrypt>=3,<4` in pyproject.toml |
| email-validator missing | startup crash | `pydantic[email]` in deps |
| python-multipart missing | upload 500 | added to deps |
| setuptools.backends.legacy not found | image build fails | changed to `setuptools.build_meta` |
| Migration 003/004 JSONB server_default | migration crash | removed server_defaults; use Python-side `default=list` |
| Ollama healthcheck uses curl (not in image) | worker never starts | changed to `["CMD","ollama","list"]` |
| Redis socket_timeout=5s races BLOCK_MS=5000 | worker crashes every 5s | `socket_timeout=30` in pool config |
| Worker ORM registry incomplete | first DB op fails | `import app.models` in pipeline.py |
| `_generate_stream` returned unawaited coroutine | Q&A 500 | added `await` to the call |
| Web fetch no User-Agent | Wikipedia/CDN 403 | added browser-like UA to httpx |
| top_k=10 → 4000-token context → 2+ min TTFT | Q&A hangs | `top_k=3` via config (was hardcoded) |
| fetchMe throws 401 on stale localStorage token | login loop | catch + clear token in fetchMe |
| nginx routed `/api/*` → FastAPI, bypassing BFF | auth 404 | route everything through Nuxt |
| auth store read `data.token` not `data.access_token` | login loop | fixed field name |
| SSE `.trim()` stripped leading space tokens | words run together | strip exactly one separator space |
| list_paths missing selectinload(concepts) | learning paths list 500 | added selectinload |
| add_source/add_file_to_board lazy source load | board source add 500 | `_reload_item()` after commit |
| fork_board missing `kb_id` on new Source records | fork KB sources returns 0 | stamp `kb_id=kb.id` on forked sources |

---

## Known Limitations (not bugs, deliberate MVP scope)

1. **Curriculum generates 1 concept per heading group.** With a single indexed source (e.g., one Wikipedia article), the chunker typically produces 1-2 heading groups → 1-2 concepts. More sources = more concepts.

2. **Upload sources in fork re-ingest from MinIO.** URL sources re-fetch from the web. Upload sources fall back to MinIO (if not expired from Redis). Duplicate network traffic; shared ingestion cache is a V2 feature.

3. **No session persistence across Colima restart.** If `colima stop && colima start`, the Postgres data volume persists but the docker socket path changes. Re-run `export DOCKER_HOST=...`.

4. **MC answer grading is exact-match.** Fragile for longer answers; works for current short correct answers from the curriculum agent.

5. **`VISIBILITY_S=300` is unsafe with >1 worker replica.** A 20-min curriculum job would be reclaimed and duplicated by a second worker after 5 min. Safe for single-worker; raise before scaling.

---

## What Comes Next

**v0.4.0 released 2026-08-04** — the June backlog shipped: private concept notes, learner progress, KB semantic+keyword search, explore assets tab, learning-page auth guards (KC-047–052). Migration head is now **011**.

All previously listed candidates shipped in v0.5.0; the two concrete leftovers shipped in v0.5.1 (KC-058 board-KB visibility sync, KC-059 sources trailing-slash fix).

**Organisations designed (2026-08-05):** `docs/09-organisations.md` supersedes OQ-3 — `team` = same org via nullable `users.org_id` + rotatable invite codes, Default-org backfill preserves existing behaviour, SQL-predicate enforcement (no JWT changes). Proposed sprint v0.6.0 = KC-060–064 (schema → domain → predicate rewire → `/org` page → three-user live verification). Not started.

New API surface in v0.3.0: `GET/POST` eval cases via versions, `GET /harnesses/{id}/eval` (run list), `POST /boards/{id}/assets` (asset → board projection), async `POST /boards/{id}/generate-summary` (202 + `board.summary.jobs` stream + `summary_status` poll), owner-authenticated `GET /boards/{id}`.

**Gotchas learned this sprint:**
- Nitro's typed-router `$fetch` hit TS "excessive stack depth" when the server route count grew — all server BFF routes now import `ofetch` explicitly; new BFF files must do the same (or use `proxyRequest`).
- After `await db.rollback()` on an async session, every ORM instance (including the request's `User`) is expired and attribute access raises MissingGreenlet — capture scalars before any flush that can raise, and re-select what you need afterwards.

### Sprint complete — v0.2.0 AI Assets Pillar released

All KC-032–040 are done and live-verified. `main` tagged v0.2.0.

```
✅KC-032 → ✅KC-033 → ✅KC-034 → ✅KC-035 → ✅KC-036 → ✅KC-037 → ✅KC-038 → ✅KC-039 → ✅KC-040
schema       asset      harness    eval        project    asset    harness  drift      search
             svc        svc        worker      svc        UI       UI       alert
```

### KC-038 notes (for reference)

**Known limitation:** Eval cases (`EvalCase` rows) have no API endpoint to create them. The `eval_suite` asset version must have cases seeded directly in the database for eval to grade anything. The eval worker runs successfully with 0 cases (returns `{total:0, passed:0, pass_rate:0.0}`). The compose page shows a note about this when eval returns 0 cases.

**Role strings are load-bearing:** `eval_suite` and `system_prompt` roles are hardcoded in `worker/eval.py:98,121`. The UI uses a constrained dropdown — no free-text role input.

**Models BFF:** `GET /api/models` → proxies to `http://ollama:11434/api/tags`. Returns `{models: string[]}`. Returns empty array if Ollama is unreachable (soft failure).

**Version meta enrichment:** On compose page mount, all accessible assets are fetched in parallel (summaries + full details) to build a `versionId → {assetTitle, versionNum, modelPin, status}` map for slot display.

**Eval SSE pattern:** Uses `fetch()` + `ReadableStream` (not `EventSource`) so the Bearer token can be sent. Same pattern as `useStreamingQuery`.

### KC-037 notes (for reference)

Auth lesson: all asset/harness endpoints require auth. Pages use `middleware: 'auth'` + client-side `$fetch` with `Bearer ${auth.token}` (NOT SSR useFetch — the token is client-only from Pinia/localStorage).

BFF routes added:
- `server/api/assets/index.get.ts` / `index.post.ts` — list/create
- `server/api/assets/[...path].ts` — catch-all for all sub-paths (via `proxyRequest`)
- Same for `server/api/harnesses/`

Syntax highlighting: `@shikijs/vue` was NOT in package.json — the handoff was wrong. Plain `<pre>` with monospace styling used instead. To add Shiki later: install it and wrap in `<ClientOnly>` to avoid SSR config pain, then rebuild frontend.

### KC-038 frontend entry point

KC-038: `/harnesses/[id]/compose` for adding/swapping asset versions by role; eval submission panel (Ollama model selector, run button, SSE progress); eval result view (aggregate score, per-case pass/fail + latency table); fork dialog reusing the board fork component pattern.

Existing BFF routes already created for harnesses:
- `server/api/harnesses/index.get.ts` — list
- `server/api/harnesses/index.post.ts` — create
- `server/api/harnesses/[...path].ts` — catch-all (fork, add-slot, swap-slot, eval submit, eval status, SSE stream)

SSE eval events route: `GET /api/v1/harnesses/{id}/eval/{run_id}/events` — the SSE stream uses `text/event-stream`. The catch-all BFF `proxyRequest` already handles this; frontend uses `EventSource` or `ReadableStream` on the client.

For the Ollama model selector: call `GET http://localhost/api/v1/harnesses/...` to get the harness, then for available models call direct to `http://ollama:11434/api/tags` via a BFF route (or use a dedicated `server/api/models/index.get.ts` proxy).

```bash
# See available Ollama models:
docker compose exec ollama ollama list
```

### Key architectural decisions for this sprint

**New Redis stream:** `eval.jobs` — add to `_STREAMS` dict in `worker/__main__.py` alongside existing `ingestion.jobs` and `curriculum.jobs`. Handler lives in `worker/eval.py`.

**New Source type:** `prompt_asset` — add to `Source.type` enum in Migration 006 (string column, no Postgres enum, same pattern as existing types). Projection service uses this type.

**Harness fork mirrors board fork exactly.** Reuse the `fork_board()` pattern: copy join-table rows, increment parent `fork_count`, populate `fork_lineage` array. Do not abstract — stay explicit.

**Eval runs are Ollama-local only.** If `model_pin` on an AssetVersion is not available in Ollama (`ollama list`), `POST /harnesses/{id}/eval` returns 422 with a message listing available models. No silent cloud fallback.

**Team visibility = all users on this instance.** No `organisations` table yet. `GET /api/v1/assets?visibility=team` returns assets visible to any registered user. Document as instance-scoped sharing in the API response.

**EvalCase is immutable per AssetVersion.** To add test cases to an eval suite, commit a new AssetVersion. The new version gets a new `version_num`; the old version's cases are untouched.

**Explore page: tab, not new route.** Add a "Harnesses" tab to the existing `/explore` page alongside KBs and Boards. No new top-level nav item.

### Deferred (do not start this sprint)

- KC-030: Async board summary (defer until multi-source boards exist)
- Free-text MC input (normalised grading already supports it — UI work only when prioritised)
- Harness fork-compare diff view (Tier 2, after KC-040)
- Cloud model eval adapter (Tier 3)

---

## Architectural Invariants (don't break these)

| Invariant | Where | Why |
|---|---|---|
| `docker build --no-cache -t knomms-api:latest ./backend` AND `-t knomms-worker:latest ./backend` | build scripts | api and worker are different image names; Colima cache bug silently ships stale code |
| After rebuilding api/frontend, run `docker compose restart nginx` (not `nginx -s reload`) | nginx restart | Colima volume sync lag means `-s reload` reads a truncated file; full restart avoids it |
| Each KB has its own isolated `vector_namespace` | KB creation, fork | Enables per-KB retrieval without namespace bleed |
| `VISIBILITY_S=300` safe for single worker only — raise before scaling | `__main__.py` | Two workers = stale reclaim duplicates a 20-min curriculum job |
| Fork creates new Source records (new IDs) | `fork_board()` | Dedup keyed on (content_hash, source_id); same source_id = no new chunks |
| `source.kb_id` stamped at creation time | ingestion service, fork, board add | `GET /v1/kbs/{id}/sources` relies on this |
| All requests through Nuxt (nginx `location /`) | nginx.conf | BFF routes unreachable if nginx bypasses Nuxt |
| `fetchMe` catches all errors silently | stores/auth.ts | Stale localStorage tokens must not surface as unhandled 401 |
| `top_k` and `ollama_read_timeout` from settings | config.py | Hardware-specific values must not be hardcoded |
| Alembic uses `DATABASE_SYNC_URL` | alembic/env.py | asyncpg not usable by Alembic |
