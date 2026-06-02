# Session Handoff — Knowledge Comms

**Session date:** 2026-06-02  
**State:** v0.1.0 released — KC-029 (MC grading) done, PR #4 merged, tag pushed  
**Branch:** `main` and `development` in sync at v0.1.0  
**Tests:** 69/69 backend (pytest) · 0 TypeScript errors (vue-tsc)  
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

v0.1.0 is tagged and released (GitHub PR #4). Clean slate for next session.

**Remaining backlog:**
- KC-030: Async board summary — defer until boards have multiple sources
- Future: free-text MC input (normalised grading already supports it)

---

## Architectural Invariants (don't break these)

| Invariant | Where | Why |
|---|---|---|
| `docker build --no-cache -t knomms-api:latest ./backend` AND `-t knomms-worker:latest ./backend` | build scripts | api and worker are different image names; Colima cache bug silently ships stale code |
| Each KB has its own isolated `vector_namespace` | KB creation, fork | Enables per-KB retrieval without namespace bleed |
| `VISIBILITY_S=300` safe for single worker only — raise before scaling | `__main__.py` | Two workers = stale reclaim duplicates a 20-min curriculum job |
| Fork creates new Source records (new IDs) | `fork_board()` | Dedup keyed on (content_hash, source_id); same source_id = no new chunks |
| `source.kb_id` stamped at creation time | ingestion service, fork, board add | `GET /v1/kbs/{id}/sources` relies on this |
| All requests through Nuxt (nginx `location /`) | nginx.conf | BFF routes unreachable if nginx bypasses Nuxt |
| `fetchMe` catches all errors silently | stores/auth.ts | Stale localStorage tokens must not surface as unhandled 401 |
| `top_k` and `ollama_read_timeout` from settings | config.py | Hardware-specific values must not be hardcoded |
| Alembic uses `DATABASE_SYNC_URL` | alembic/env.py | asyncpg not usable by Alembic |
