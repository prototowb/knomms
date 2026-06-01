# Session Handoff — Knowledge Commons

**Session date:** 2026-06-01  
**Ended at:** Milestone 1 complete  
**Branch:** `main` — all work committed directly  
**Tests:** 29/29 passing (pure unit tests on chunker + citation logic)

---

## What This Project Is

A self-hosted, zero-external-cost grounded collective intelligence platform. Three layers:
1. **Knowledge Core** — multimodal ingestion → RAG with citations → agentic synthesis
2. **Learning Layer** — AI-generated learning paths + assessments from a corpus
3. **Discovery Layer** — visual collection boards; fork → activates Knowledge Core

Full specification: `PROJECT_SPECIFICATIONS.md` → `docs/` for deep-dives.  
Tech stack summary: `README.md`.

---

## What Was Built This Session

### Specification phase (no code)

8 architecture documents written from scratch using parallel subagents, then synthesized:

| Doc | Contents |
|---|---|
| `docs/00-vision.md` | Platform thesis, 7 AI principles, design bets |
| `docs/01-product-spec.md` | 5 personas, capability tables, 3 user journeys |
| `docs/02-ai-architecture.md` | Ingestion pipeline, embedding, RAG, LangGraph agents, guardrails |
| `docs/03-learning-layer.md` | Curriculum agent, data model, assessment, spaced repetition |
| `docs/04-discovery-layer.md` | Board UI, fork mechanic, semantic recommendations |
| `docs/05-platform-architecture.md` | Service decomposition, ER sketch, auth, search, cost model |
| `docs/06-roadmap.md` | MVP scope tables, milestones, hardware sizing |
| `docs/07-frontend-architecture.md` | Vue 3/Nuxt 3, Tailwind, streaming patterns |
| `docs/08-backend-architecture.md` | FastAPI structure, SQLAlchemy, worker, testing |

Key decisions made during spec: self-hosted/zero-cost (Ollama, pgvector, MinIO, Redis, Docker Compose), Tailwind over SCSS/BEM, modular monolith over 7 microservices.

### Infrastructure (proto-gear + PROJECT_SPECIFICATIONS.md)

- `pg init` run with `--all --with-capabilities --with-branching --ticket-prefix KC`
- `PROJECT_SPECIFICATIONS.md` written as the agent entry point (this is what `AGENTS.md` expects)
- `PROJECT_STATUS.md` updated with real project state

### Milestone 0 — Infrastructure Baseline (commit `6bb3ef6`)

| File | Purpose |
|---|---|
| `docker-compose.yml` | All 7 services: db, redis, minio, ollama, api, worker, frontend, nginx |
| `.env.example` | All required env vars |
| `nginx/nginx.conf` | Plain HTTP reverse proxy; SSE buffering disabled; WS upgrade |
| `backend/Dockerfile` | python:3.12-slim + uvicorn; installs `.[ingestion]` |
| `frontend/Dockerfile` | node:20-alpine multi-stage build |
| `backend/pyproject.toml` | All M0 deps; ingestion/ai extras for later milestones |
| `backend/app/core/` | `config.py` (pydantic-settings), `db.py` (SQLAlchemy async engine), `redis.py`, `security.py` (JWT HS256 + bcrypt) |
| `backend/app/models/` | `User`, `Source`, `Chunk` (pgvector `Vector(768)` + HNSW index), `KnowledgeBase`, `Collection`/`CollectionItem` |
| `backend/alembic/versions/001_baseline.py` | `CREATE EXTENSION IF NOT EXISTS vector` first, then all 5 tables |
| `backend/app/domains/identity/` | `register`, `login`, `refresh`, `/me` endpoints |
| `backend/app/main.py` | App factory, lifespan, CORS, `/health` |
| `frontend/` | Nuxt 3 scaffold: hybrid SSR/SPA routing, Tailwind semantic tokens, Pinia auth store, `useStreamingQuery` SSE composable, BFF server routes |

**To run Milestone 0 on a machine with Docker:**
```bash
cp .env.example .env              # fill POSTGRES_PASSWORD, SECRET_KEY, MINIO_ROOT_PASSWORD
docker compose up -d db redis minio
docker compose run --rm api alembic upgrade head
docker compose up -d
# Frontend: http://localhost   API docs: http://localhost/api/docs
```

### Milestone 1 — Ingestion Loop + Grounded Q&A (commit `cbb34da`)

**Three contracts pinned before writing any code:**

1. `RawBlock` — the extractor→chunker contract (defined in `blocks.py`)
2. Redis job-message shape — `{source_id, user_id, kb_id, vector_namespace, upload}` published to stream `ingestion.jobs`
3. SSE event format — must match `frontend/composables/useStreamingQuery.ts`:
   - `event: citations\ndata: <JSON dict>\n\n` (sent first)
   - `data: <token>\n\n` (no `event:` field → frontend appends to `response`)

**Key seam resolved:** `Chunk.vector_namespace` (migration `002`) stamped at ingest time. Retrieval filters `WHERE vector_namespace = :ns` — no 4-hop join. Auth uses KB ownership check, not JWT `namespaces` claim (post-login KBs aren't in the claim).

| New files | Purpose |
|---|---|
| `alembic/versions/002_...py` | Adds `vector_namespace` column + index to `chunks` |
| `app/domains/ingestion/blocks.py` | `RawBlock` dataclass |
| `app/domains/ingestion/extractors/pdf.py` | pdfminer.six; heading detection by font size |
| `app/domains/ingestion/extractors/web.py` | httpx + html2text; JS-rendering deferred to M2 |
| `app/domains/ingestion/chunker.py` | Heading-boundary sections → sentence-window chunks → 20% overlap; content-hash |
| `app/domains/ingestion/service.py` | `submit_url` / `submit_file` → Redis Streams; KB auto-create |
| `app/domains/ingestion/router.py` | `POST /v1/sources`, `POST /v1/sources/upload`, `GET /v1/sources/{id}`, `WS /v1/sources/{id}/progress` |
| `app/domains/knowledge_base/service.py` | `get_or_create_default` + `get_by_id` (ownership check) |
| `app/domains/retrieval/types.py` | `RetrievedChunk` dataclass — **pure, no SQLAlchemy import** (keeps tests fast) |
| `app/domains/retrieval/service.py` | pgvector `<=>` cosine distance; `SET LOCAL hnsw.ef_search = 40` |
| `app/domains/generation/ollama.py` | Async httpx Ollama client; `generate`, `stream`, `embed` |
| `app/domains/generation/citations.py` | `build_rag_prompt`, `citations_sse_event`, `token_sse_event`, `validate_citations` |
| `app/domains/generation/service.py` | Embed query → retrieve → stream; `asyncio.Semaphore` for concurrency cap |
| `app/domains/generation/router.py` | `POST /v1/kbs/{id}/query` → `StreamingResponse` SSE |
| `app/worker/__main__.py` | `XREADGROUP` consumer; `XAUTOCLAIM` stale-job reclaim; SIGTERM handler |
| `app/worker/pipeline.py` | 7-stage pipeline: fetch → extract → chunk → dedup → embed → persist → publish |
| `app/worker/embed.py` | `embed_chunks()` batched at 32/call |
| `tests/test_chunker.py` | 13 tests — section splitting, windowing, overlap, heading prefix, hash |
| `tests/test_citations.py` | 16 tests — RAG prompt, citation extraction, hallucination detection, SSE format |

**What was deliberately NOT built in M1** (deferred per roadmap):
- Cross-encoder reranking
- Intent classification
- Multi-hop retrieval
- NLI fidelity scorer
- Playwright (JS-rendered web extraction)
- LangGraph agents (Curriculum, Assessment, Debate)
- tsvector BM25 hybrid search

---

## Current File Map

```
knowledge-commons/
├── PROJECT_SPECIFICATIONS.md   ← agent entry point (read this first)
├── PROJECT_STATUS.md           ← current tickets + state
├── AGENTS.md / CLAUDE.md       ← proto-gear orchestration
├── docker-compose.yml          ← full self-hosted stack
├── .env.example
├── nginx/nginx.conf
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/versions/
│   │   ├── 001_baseline.py     ← pgvector ext + 5 core tables
│   │   └── 002_*.py            ← vector_namespace on chunks
│   ├── app/
│   │   ├── main.py             ← FastAPI factory + /health
│   │   ├── core/               ← config, db, redis, security
│   │   ├── deps/               ← get_db, get_current_user
│   │   ├── models/             ← User, Source, Chunk, KnowledgeBase, Collection
│   │   ├── schemas/            ← Pydantic v2 request/response types
│   │   ├── domains/
│   │   │   ├── identity/       ← register, login, refresh, /me ✓ M0
│   │   │   ├── knowledge_base/ ← get_or_create_default ✓ M1
│   │   │   ├── ingestion/      ← submit, extractors, chunker ✓ M1
│   │   │   ├── retrieval/      ← pgvector cosine search ✓ M1
│   │   │   └── generation/     ← Ollama client, citations, SSE ✓ M1
│   │   └── worker/             ← Redis Streams consumer ✓ M1
│   └── tests/
│       ├── test_chunker.py     ← 13 tests ✓
│       └── test_citations.py   ← 16 tests ✓
└── frontend/
    ├── Dockerfile
    ├── nuxt.config.ts          ← hybrid SSR/SPA routing
    ├── tailwind.config.ts      ← semantic color tokens
    ├── stores/auth.ts          ← Pinia auth store ✓ M0
    ├── composables/
    │   └── useStreamingQuery.ts ← SSE consumer ✓ M0
    ├── pages/
    │   ├── index.vue
    │   ├── explore/index.vue   ← SSR public discovery page
    │   └── kb/[kbId]/index.vue ← SPA KB workspace
    └── server/api/auth/        ← Nuxt BFF proxies ✓ M0
```

---

## Known Issues / Caveats

1. **Docker not verified in this environment.** Docker was unavailable on this machine. All code is syntax-clean and unit-tested on pure logic, but the full stack (DB migrations, Redis, Ollama, MinIO, Nginx) requires a machine with Docker to verify. The first real run will surface integration issues.

2. **`SourceOut.kb_id` is set post-validation.** In `ingestion/router.py`, `kb_id` is set on the Pydantic model after `model_validate()`. This works but is fragile — should be refactored to pass `kb_id` through the source model or as a dedicated response schema when schemas are tightened up.

3. **Upload bytes held in Redis (TTL 1 hour).** File upload content is stored in Redis under `upload:{source_id}` until the worker fetches it. Large files (up to 200MB) will bloat Redis memory. For M2, move this to a MinIO presigned-URL upload flow where the client uploads directly to MinIO and the worker fetches from there.

4. **Chunker sentence splitter is punctuation-dependent.** The `_split_sentences` function relies on `.`, `!`, `?` to split. Text with no sentence-ending punctuation (e.g., list items, table cells, code) stays as one big "sentence" and can produce oversized overlap regions. A word-boundary fallback should be added in M2.

5. **`alembic/versions/__init__.py` exists but Alembic doesn't use it.** Harmless, but can be removed.

6. **Frontend `tailwind.config.ts` missing Nuxt-specific content paths.** The config scans `components/**/*.vue` etc., but Nuxt stores its auto-imports and layouts under `.nuxt/` — these are already compiled so it's fine, but double-check `content` paths once the first real Nuxt build runs.

7. **No `.gitignore` for frontend `node_modules` at repo root.** The frontend has its own `.gitignore`, but `node_modules/` may show up in `git status` if npm install is run before the root `.gitignore` covers it. Add `frontend/node_modules/` to root `.gitignore` or run `npm install` only after checking.

---

## What Comes Next — Milestone 2

From `docs/06-roadmap.md`:

> **Milestone 2 — Core AI Flows (Week 5–7)**
> - Curriculum agent: concept extraction, flat sequence, explanation generation
> - Assessment generation: MC questions with grounded distractors
> - Instructor review interface: accept / override / prune concepts
> - Learner-facing path: read explanations, attempt assessment, see grounded feedback

**The three things to resolve before writing M2 code:**

1. **LangGraph dependency.** The `ai` extra in `pyproject.toml` includes `langgraph>=0.2` and `langgraph-checkpoint-postgres>=1.0`. The Dockerfile currently installs `.[ingestion]`. Decide whether to fold `ai` into the default image or keep separate worker images.

2. **Learning path data model.** `docs/03-learning-layer.md` §3 defines the full schema (`LearningPath`, `Module`, `Concept`, `AssessmentItem`, `Citation`). Migration `003` needs to be written before the curriculum agent can persist its output. The `Citation` table is the grounding contract — write it first.

3. **Frontend KB workspace.** `pages/kb/[kbId]/index.vue` is a stub. M2 needs a real Q&A interface (the SSE composable is wired, just needs UI), plus a new `pages/learn/[pathId]/index.vue` for the learning path view.

**Suggested M2 ticket sequence:**
```
KC-013  Migration 003 — LearningPath, Module, Concept, AssessmentItem, Citation tables
KC-014  Curriculum agent (LangGraph) — concept extraction + flat sequence proposal
KC-015  Assessment agent — MC questions with grounded distractors
KC-016  Learning domain router — POST /v1/kbs/{id}/learning-paths, PATCH /v1/learning-paths/{id}/modules
KC-017  Frontend KB workspace — real Q&A UI with citation side panel
KC-018  Frontend learning path view — concept reading + MC assessment + grounded feedback
```

---

## Architectural Invariants (don't break these)

These decisions have downstream consequences — changing them requires migration:

| Invariant | Where enforced | Why |
|---|---|---|
| `CREATE EXTENSION vector` before `chunks` table | Migration 001 ordering | pgvector fails without the extension |
| `Chunk.vector_namespace` stamped at ingest time | `pipeline.py` + `chunker.py` | Enables single-WHERE retrieval; 4-hop join alternative is too slow |
| KB auth = ownership check, not JWT namespaces | `generation/service.py`, `kb/service.py` | JWT namespaces only populated at login; post-login KBs not in token |
| SSE format: `event: citations` first, then bare `data:` tokens | `citations.py` `citations_sse_event` / `token_sse_event` | Must match `useStreamingQuery.ts` frontend contract exactly |
| `RetrievedChunk` lives in `retrieval/types.py` (not `service.py`) | Import structure | Keeps citation tests free of SQLAlchemy; any move breaks test imports |
| `EMBED_BATCH_SIZE = 32` in `worker/embed.py` | Ollama processes one text at a time | Batching is client-side; changing this affects throughput, not correctness |
| Alembic uses `DATABASE_SYNC_URL` (not `DATABASE_URL`) | `alembic/env.py` | `DATABASE_URL` uses `postgresql+asyncpg://`; Alembic needs the sync driver |

---

## How to Re-orient in a New Session

```bash
# 1. Read project state
cat PROJECT_STATUS.md

# 2. Read specs entry point
cat PROJECT_SPECIFICATIONS.md

# 3. Confirm tests still pass
cd backend && python3 -m pytest tests/ -q

# 4. See what's committed
git log --oneline -10

# 5. Check for any uncommitted work
git status
```

The `CLAUDE.md` file (auto-generated by proto-gear) loads the project context automatically in Claude Code sessions — you don't need to manually reference it.
