# Session Handoff — Knowledge Commons

**Session date:** 2026-06-01  
**Ended at:** Milestone 3 complete  
**Branch:** `main` — all work committed directly  
**Tests:** 59/59 passing (chunker, citations, learning agent, curation)

---

## What This Project Is

A self-hosted, zero-external-cost grounded collective intelligence platform. Three layers:
1. **Knowledge Core** — multimodal ingestion → RAG with citations → agentic synthesis
2. **Learning Layer** — AI-generated learning paths + assessments from a corpus
3. **Discovery Layer** — visual collection boards; fork → activates Knowledge Core

Full specification: `PROJECT_SPECIFICATIONS.md` → `docs/` for deep-dives.

---

## What Was Built (Cumulative)

### Milestone 0 — Infrastructure Baseline (`6bb3ef6`)
Docker Compose stack, env, nginx, Dockerfiles, pyproject.toml, core modules, ORM models (User/Source/Chunk/KnowledgeBase/Collection), Alembic migration 001 (pgvector + 5 tables), identity domain (register/login/refresh/me), Nuxt 3 frontend scaffold.

### Milestone 1 — Ingestion Loop + Grounded Q&A (`cbb34da`)
Migration 002 (vector_namespace on chunks), ingestion domain (PDF/web extractors, semantic chunker, service, router), retrieval domain (pgvector cosine), generation domain (Ollama client, citation injection, SSE streaming), Redis Streams worker. 29 unit tests.

### Milestone 2 — Core AI Flows (`bcfb0b4`)
Migration 003 (learning_paths/path_concepts/assessment_items/distractors), curriculum agent (heading-heuristic grouping + Ollama JSON, no LangGraph), learning service + router (6 endpoints), frontend KB workspace (Q&A + citations), learning path list + detail views with MC assessment + instructor controls, 6 BFF routes. 55 tests.

### Milestone 3 — Discovery Surface (`6486922`)

**Key pre-code decisions:**
1. **"A Board is a Collection with richer layout_config. No separate Board table."** — confirmed from `docs/05-platform-architecture.md`. Extended the existing Collection model instead of a new entity.
2. **Fork dedup keyed on (content_hash, source_id)** — confirmed from `worker/pipeline.py`. Forking creates new Source records (new IDs), so dedup passes and chunks get the fork KB's namespace. Fork works correctly.
3. **MinIO fallback** — added to `pipeline._fetch_content` so upload sources in forks re-ingest from MinIO instead of failing on expired Redis key.
4. **Auth-optional public endpoints** — added `get_optional_user` dep so SSR board/explore/profile fetches don't 401.

| New file | Purpose |
|---|---|
| `alembic/versions/004_discovery_layer.py` | Extends collections (layout_config, ai_summary, board_embedding vector(768), fork_count) + collection_items.lane |
| `app/models/collection.py` | Updated with all new columns (board_embedding uses pgvector Vector(768)) |
| `app/core/storage.py` | MinIO client wrapper (lazy init) |
| `app/worker/pipeline.py` | MinIO fallback in `_fetch_content` for forked upload sources |
| `app/deps/auth.py` | `get_optional_user` — returns User or None without requiring auth |
| `app/domains/curation/types.py` | `build_fork_lineage` pure helper |
| `app/domains/curation/service.py` | BoardService: create, get_public_board, list_public_boards, fork_board, add_source, search_boards_semantic, get_curator_profile, generate_board_summary, update_board_embedding |
| `app/schemas/curation.py` | Pydantic schemas for boards, items, curator profile |
| `app/domains/curation/router.py` | 8 endpoints (see below) |
| `frontend/nuxt.config.ts` | Added `/board/**` SSR routeRule |
| `frontend/pages/explore/index.vue` | Rewritten: trending grid + client-side semantic search |
| `frontend/pages/board/[boardId]/index.vue` | Swim-lane view, source cards, fork dialog (SSR) |
| `frontend/pages/u/[handle]/index.vue` | Curator profile with board grid (SSR) |
| `frontend/pages/kb/[kbId]/learn/index.vue` | Fixed template parse bug (nested double-quotes in placeholder) |
| 8 BFF routes | /api/boards/{get,post,search}, /api/boards/[id]/{get,fork,sources,generate-summary}, /api/u/[handle] |
| `tests/test_curation.py` | 4 fork lineage tests |

**API endpoints added:**
- `GET /v1/boards` — list public boards (trending or recent, quality floor applied)
- `GET /v1/boards/search?q=...` — semantic search via board_embedding centroid
- `GET /v1/boards/{board_id}` — get public board with items + sources
- `POST /v1/boards` — create board (auth required)
- `POST /v1/boards/{board_id}/fork` — fork a public board (auth required)
- `POST /v1/boards/{board_id}/sources` — add URL source to board (auth required)
- `POST /v1/boards/{board_id}/generate-summary` — generate AI summary (auth required)
- `GET /v1/u/{handle}` — curator profile with public boards

---

## Current File Map

```
knowledge-commons/
├── PROJECT_SPECIFICATIONS.md
├── PROJECT_STATUS.md
├── AGENTS.md / CLAUDE.md
├── docker-compose.yml
├── .env.example
├── nginx/nginx.conf
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic/versions/
│   │   ├── 001_baseline.py
│   │   ├── 002_add_vector_namespace_to_chunks.py
│   │   ├── 003_learning_layer.py
│   │   └── 004_discovery_layer.py          ← M3
│   ├── app/
│   │   ├── main.py
│   │   ├── core/               ← config, db, redis, security, storage ✓ M3
│   │   ├── deps/               ← get_db, get_current_user, get_optional_user ✓ M3
│   │   ├── models/             ← User, Source, Chunk, KB, Collection (extended), Learning ✓ M3
│   │   ├── schemas/            ← user, source, kb, learning, curation ✓ M3
│   │   ├── domains/
│   │   │   ├── identity/       ← ✓ M0
│   │   │   ├── knowledge_base/ ← ✓ M1
│   │   │   ├── ingestion/      ← ✓ M1
│   │   │   ├── retrieval/      ← ✓ M1
│   │   │   ├── generation/     ← ✓ M1
│   │   │   ├── learning/       ← ✓ M2
│   │   │   └── curation/       ← service, router, schemas, types ✓ M3
│   │   └── worker/             ← MinIO fallback added ✓ M3
│   └── tests/
│       ├── test_chunker.py         ← 13 tests
│       ├── test_citations.py       ← 16 tests
│       ├── test_learning_agent.py  ← 26 tests
│       └── test_curation.py        ← 4 tests
└── frontend/
    ├── Dockerfile
    ├── nuxt.config.ts          ← /board/** SSR added ✓ M3
    ├── tailwind.config.ts
    ├── stores/auth.ts
    ├── composables/useStreamingQuery.ts
    ├── pages/
    │   ├── index.vue
    │   ├── explore/index.vue        ← real trending + search ✓ M3
    │   ├── board/[boardId]/         ← swim-lane view, fork dialog ✓ M3
    │   ├── u/[handle]/              ← curator profile ✓ M3
    │   ├── kb/[kbId]/
    │   │   ├── index.vue
    │   │   └── learn/index.vue
    │   └── learn/[pathId]/index.vue
    └── server/api/
        ├── auth/
        ├── kb/[kbId]/
        ├── learning-paths/[pathId]/
        ├── boards/                  ← 4 board routes ✓ M3
        ├── boards/[boardId]/        ← 4 board-scoped routes ✓ M3
        └── u/[handle]/              ← curator profile ✓ M3
```

---

## Known Issues / Caveats

1. **Docker not verified.** All three milestones were built without Docker. All Ollama-dependent paths (generation, curriculum agent, board semantic search, board summary generation, board embedding computation) require Docker for integration verification.

2. **board_embedding centroid is never automatically updated.** `update_board_embedding` exists on BoardService but is never called automatically. It should be triggered after each successful source ingestion (via the `source.embedded` Redis pub/sub event the pipeline publishes). Wire this up in M4.

3. **Fork creates bare KB (no `forked_from` metadata).** `fork_board` creates a new KB via `get_or_create_default` but doesn't record that the KB was seeded from a fork. The spec requires "fork lineage recorded with attribution." The Collection carries the lineage, but the KB itself has no `forked_from_collection_id` column. Add in M4 if needed.

4. **MC answer grading is exact-match** (M2 carryover). Fragile for longer answers.

5. **`SourceOut.kb_id` is set post-validation** (M1 carryover). Fragile Pydantic anti-pattern.

6. **Upload bytes held in Redis (TTL 1 hour)** (M1 carryover). Large files bloat Redis memory. MinIO fallback in M3 mitigates this for forked sources, but original ingestion still uses Redis.

7. **`/api/boards/search` route conflicts with `/api/boards/[boardId]`** — Nuxt file-system routing may route `/api/boards/search` to `[boardId]/index.get.ts` with `boardId = "search"` before hitting `search.get.ts`. Test the routing when the stack runs; if it conflicts, rename to `/api/boards-search.get.ts` and update the `$fetch` call.

---

## What Comes Next — Milestone 4 / Cross-cutting

With all three layers now wired end-to-end, M4 should focus on:

1. **Wire board_embedding updates** — subscribe to `source.embedded` pub/sub event in the worker and call `update_board_embedding`. This makes semantic recommendations live.

2. **Integration run** — first real Docker Compose `up`. This surfaces all the unverified integration issues across M0–M3. Expect: migration ordering, Ollama model pull, MinIO bucket creation, CORS, SSE buffering.

3. **Frontend auth flow** — the current `stores/auth.ts` stores the token in localStorage and the `pages/index.vue` is a stub. M4 needs: login page, register page, redirect logic for authenticated routes.

4. **Board update_board_embedding trigger** — see item 2 above.

5. **KB-to-board linkage** — when a user forks a board, the new Collection should be linked to the new KB via the `knowledge_base_collection` join table. Currently `fork_board` creates the KB but doesn't set this link.

---

## Architectural Invariants (don't break these)

| Invariant | Where enforced | Why |
|---|---|---|
| `CREATE EXTENSION vector` before `chunks` table | Migration 001 ordering | pgvector fails without the extension |
| `Chunk.vector_namespace` stamped at ingest time | `pipeline.py` + `chunker.py` | Enables single-WHERE retrieval |
| KB auth = ownership check, not JWT namespaces | `generation/service.py`, `kb/service.py` | JWT namespaces only populated at login |
| SSE format: `event: citations` first, then bare `data:` tokens | `citations.py` | Must match `useStreamingQuery.ts` |
| `RetrievedChunk` lives in `retrieval/types.py` | Import structure | Keeps citation tests free of SQLAlchemy |
| `ConceptProposal` / `PassageDraft` live in `learning/types.py` | Import structure | Keeps learning agent tests free of SQLAlchemy |
| `build_fork_lineage` lives in `curation/types.py` | Import structure | Keeps curation tests free of FastAPI/SQLAlchemy |
| `_ollama_generate` is a module-level wrapper in `agent.py` | Test patchability | Deferred import so agent.py loads without httpx |
| Fork dedup keyed on `(content_hash, source_id)` | `worker/pipeline.py` `_dedup()` | New source_id in fork → fresh chunks with correct namespace |
| Alembic uses `DATABASE_SYNC_URL` | `alembic/env.py` | `DATABASE_URL` uses asyncpg; Alembic needs sync driver |

---

## How to Re-orient in a New Session

```bash
cd backend && python3 -m pytest tests/ -q   # 59 tests should pass
git log --oneline -6                          # 4 milestone commits + 2 doc commits
git status                                    # should be clean
```
