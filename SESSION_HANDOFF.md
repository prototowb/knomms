# Session Handoff — Knowledge Comms

**Session date:** 2026-06-05  
**State:** v0.2.0 in progress — KC-032–036 + KC-040 code complete; KC-037 (frontend asset library) is next  
**Branch:** `development` ahead of `main`; `main` at v0.1.0  
**Tests:** 79/79 backend (pytest) · 0 TypeScript errors (vue-tsc)  
**Live verification:** KC-033–036, KC-040 are code-complete but NOT live-verified on Colima (run `alembic upgrade head` + smoke test before marking ✅)  
**Stack:** Running on Colima (macOS) — see §Dev Runtime

---

## How to Re-orient

```bash
# 1. Start the stack (if not running)
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"
docker compose up -d

# 2. Run models if not loaded
docker compose run --rm ollama-init

# 3. Verify
curl http://localhost/api/health          # {"status":"ok"}
cd backend && python3 -m pytest tests/ -q  # 59 passed
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
| Layer 4 (AI Assets) | AssetService CRUD | ⚠ code complete | KC-033 — POST/GET/list/deprecate at /api/v1/assets; needs live smoke test |
| Layer 4 (AI Assets) | HarnessService CRUD | ⚠ code complete | KC-034 — create/fork/get/list/add-slot/swap-slot at /api/v1/harnesses |
| Layer 4 (AI Assets) | Eval worker | ⚠ code complete | KC-035 — eval.jobs stream; grades EvalCase records; SSE progress; 422 on missing model |
| Layer 4 (AI Assets) | Asset projection | ⚠ code complete | KC-036 — POST /assets/{id}/versions/{num}/project → prompt_asset Source → ingestion.jobs |
| Layer 4 (AI Assets) | Asset FTS | ⚠ code complete | KC-040 — GET /assets?q= with tsvector GIN; Migration 007 (run alembic upgrade head) |

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

v0.1.0 is shipped. v0.2.0 sprint is **AI Assets Pillar** — a fourth pillar for practitioner teams building with AI. Full ticket details in `PROJECT_STATUS.md §Active`.

### Sprint entry point: KC-037

All backend tickets (KC-033–036, KC-040) are code complete. Wall hit at frontend. Next session starts with KC-037 (asset library UI).

```
✅KC-032 → ✅KC-033 → ✅KC-034 → ✅KC-035 → ✅KC-036 → KC-037 → KC-038 → KC-039 → ✅KC-040
schema       asset      harness    eval        project    asset    harness  drift    search
             svc        svc        worker      svc        UI       UI       alert
```

**⚠ Live verification pending for KC-033–036, KC-040:**

```bash
# 0. Apply migration 007 (GIN indexes)
docker compose exec api alembic upgrade head

# 1. Rebuild API + worker (Colima cache bug — always use --no-cache)
docker build --no-cache -t knomms-api:latest ./backend
docker build --no-cache -t knomms-worker:latest ./backend
docker compose up --force-recreate -d api worker
docker compose restart nginx

# 2. Get a token
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@localhost.dev","password":"devdev99"}' | jq -r .access_token)

# 3. Create an asset
ASSET=$(curl -s -X POST http://localhost/api/v1/assets \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"My Prompt","asset_type":"system_prompt","visibility":"private"}')
ASSET_ID=$(echo $ASSET | jq -r .id)

# 4. Add a version
curl -s -X POST http://localhost/api/v1/assets/$ASSET_ID/versions \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"content":"You are a helpful assistant.","rationale":"initial version"}'

# 5. List assets (search)
curl -s "http://localhost/api/v1/assets?q=helpful" \
  -H "Authorization: Bearer $TOKEN" | jq .

# 6. Create a harness
curl -s -X POST http://localhost/api/v1/harnesses \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Test Harness","visibility":"private"}' | jq .
```

### KC-037 frontend entry point

KC-037 is the asset library UI. Look at `/frontend/pages/boards.vue` (board list page) and `/frontend/pages/board/[boardId].vue` (board detail page) as the direct analogues — asset pages follow the same patterns.

Key frontend patterns to reuse:
- Auth token from Pinia store: `const auth = useAuthStore(); auth.token`
- SSR data fetch: `useFetch('/api/assets', { headers: ... })` via BFF route
- BFF route template: copy `server/api/boards/[...path].ts` → `server/api/assets/[...path].ts`
- Syntax highlighting: `@shikijs/vue` (Shiki) already available for YAML/JSON content

New BFF routes needed:
- `server/api/assets/[...path].ts` → proxies to FastAPI `/v1/assets`
- `server/api/harnesses/[...path].ts` → proxies to FastAPI `/v1/harnesses`

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
