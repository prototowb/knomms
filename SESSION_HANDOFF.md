# Session Handoff — Knowledge Commons

**Session date:** 2026-06-01  
**Ended at:** Milestone 4 complete  
**Branch:** `main` — all work committed directly  
**Tests:** 59/59 backend (pytest) · 0 TypeScript errors (vue-tsc)

---

## What This Project Is

A self-hosted, zero-external-cost grounded collective intelligence platform. Three layers:
1. **Knowledge Core** — multimodal ingestion → RAG with citations → agentic synthesis
2. **Learning Layer** — AI-generated learning paths + assessments from a corpus
3. **Discovery Layer** — visual collection boards; fork → activates Knowledge Core

Full specification: `PROJECT_SPECIFICATIONS.md` → `docs/` for deep-dives.

---

## How to Re-orient

```bash
# Backend tests
cd backend && python3 -m pytest tests/ -q        # 59 should pass

# Frontend typecheck (node/npm available in this env)
cd frontend && npm install && npx nuxt prepare && npx vue-tsc --noEmit -p tsconfig.json

# Git state
git log --oneline -10
git status
```

**Docker is unavailable in this dev environment.** All Ollama/pgvector/MinIO/Redis paths are untested until a Docker run. This includes: Q&A generation, curriculum agent, board semantic search, board summary, board embedding computation. The first `docker compose up` is the key next step.

---

## Milestone History

| Milestone | Commit | Tests | What shipped |
|---|---|---|---|
| M0 — Infrastructure | `6bb3ef6` | — | Docker Compose, Alembic 001, identity domain, Nuxt scaffold |
| M1 — Ingestion + Q&A | `cbb34da` | 29 | PDF/web extractors, chunker, retrieval, Ollama SSE streaming, Redis worker |
| M2 — Learning layer | `bcfb0b4` | 55 | Migration 003, curriculum agent, learning path API + UI |
| M3 — Discovery layer | `6486922` | 59 | Migration 004, boards, fork, explore, curator profiles |
| M4 — Auth + integration | `f2e9bcc` | 59 | Auth flow, dashboard, fork-KB fix, board embeddings, typecheck baseline |

---

## Key Decisions Made in M4

1. **Fork-KB isolation bug fixed.** `fork_board` was calling `get_or_create_default(user)` which returns the user's single default KB. All forks would share one `vector_namespace`, making cross-fork retrieval bleed. Fixed to `kb_svc.create(user, title)` (always creates a new KB with a fresh namespace). The `knowledge_base_collection` join row is now inserted correctly.

2. **TypeScript typecheck baseline established.** `vue-tsc --noEmit` now passes clean across all 9 pages + 24 BFF routes. The 4 errors found:
   - Inline `$fetch` in template `@click` handlers (learn page) → extracted to methods
   - `me.get.ts` implicit any → `Promise<unknown>` return type
   - `publish.post.ts` excessive stack depth → `$fetch<unknown>`
   - `User` interface missing `display_name` field

3. **Board embedding Stage 8.** `_refresh_board_embeddings` runs inline after each ingestion completes — no separate subscriber process. It recomputes the centroid average of all non-overlap chunk embeddings for every collection containing the just-indexed source.

4. **BFF auth pattern clarified.** `auth/login.post.ts` uses `X-Internal-Secret` header. All other BFF routes forward only the client `Authorization: Bearer` token. The backend validates the JWT on each request — `X-Internal-Secret` is only used for the login/register BFF routes as an internal trust signal. This is consistent but should be verified in the first integration run.

---

## Current File Map

```
knowledge-commons/
├── backend/
│   ├── alembic/versions/001–004        ← 4 migrations
│   ├── app/
│   │   ├── core/               ← config, db, redis, security, storage
│   │   ├── deps/               ← get_db, get_current_user, get_optional_user
│   │   ├── models/             ← User, Source, Chunk, KB, Collection, Learning
│   │   ├── schemas/            ← all domains
│   │   └── domains/
│   │       ├── identity/       ← register, login, refresh, /me
│   │       ├── knowledge_base/ ← service, router (list + create KBs)
│   │       ├── ingestion/      ← extractors, chunker, service, router
│   │       ├── retrieval/      ← pgvector cosine search
│   │       ├── generation/     ← Ollama, citations, SSE
│   │       ├── learning/       ← agent, service, router (6 endpoints)
│   │       └── curation/       ← service, router (8 endpoints)
│   ├── worker/                 ← Redis Streams consumer + 8-stage pipeline
│   └── tests/                  ← 59 tests (chunker, citations, learning, curation)
└── frontend/
    ├── plugins/auth.client.ts  ← restores session from localStorage
    ├── middleware/auth.ts      ← route guard → /login?redirect=...
    ├── layouts/default.vue     ← sidebar nav + user info + logout
    ├── pages/
    │   ├── login.vue           ← auth form (no layout)
    │   ├── register.vue        ← register form (no layout)
    │   ├── index.vue           ← dashboard: KB list + create KB
    │   ├── explore/            ← trending boards + semantic search (SSR)
    │   ├── board/[boardId]/    ← swim-lane view + fork dialog (SSR)
    │   ├── u/[handle]/         ← curator profile (SSR)
    │   ├── kb/[kbId]/          ← Q&A + citation sidebar
    │   ├── kb/[kbId]/learn/    ← learning path list + generate
    │   └── learn/[pathId]/     ← path detail + MC assessment
    └── server/api/
        ├── auth/               ← login, register, me
        ├── kbs/                ← GET/POST (list + create)
        ├── kb/[kbId]/          ← learning-paths GET/POST
        ├── learning-paths/     ← get, publish, patch concept, attempt
        ├── boards/             ← GET, POST, search
        ├── boards/[boardId]/   ← get, fork, sources, generate-summary
        └── u/[handle]/         ← curator profile
```

---

## What's Left Before MVP Is Launchable

### Blocked on Docker (cannot build here)

1. **Integration run** — first `docker compose up`. Expected issues to fix:
   - Alembic migration ordering (vector extension → tables)
   - Ollama model pull step
   - MinIO bucket creation on first start
   - CORS origins match nginx/port config
   - SSE buffering in nginx (`proxy_buffering off` is set, but verify)

2. **BFF auth verification** — login/register use `X-Internal-Secret`; all other routes use forwarded `Authorization: Bearer`. Verify the backend accepts both patterns correctly.

### Buildable here (no Docker needed)

3. **Source ingestion UI** — no page exists for uploading PDFs or pasting URLs into a KB. The ingestion API (`POST /v1/sources`) exists but the KB workspace has no UI for it. Build `pages/kb/[kbId]/sources.vue` or integrate into the KB workspace.

4. **Board management UI** — no page for creating your own board, adding sources to it, or managing lanes. Could add `pages/boards/new.vue` and `pages/boards/[boardId]/edit.vue`.

5. **My Boards section** — dashboard only shows KBs. Add a section showing the user's own boards (public + private). Needs `GET /v1/my/collections` endpoint or extend the existing curation service with a user-scoped list.

6. **Public layout header** — `layouts/public.vue` doesn't show login/register links. Users arriving at `/explore` or `/board/*` have no visible path to create an account.

---

## Known Issues / Caveats

1. **`upload bytes held in Redis`** (M1 carryover) — original ingestion still uses Redis TTL. MinIO fallback exists for forks but direct uploads still need MinIO write step.

2. **`/api/boards/search` may conflict with `/api/boards/[boardId]`** in Nuxt file-routing — if Nuxt routes `GET /api/boards/search` to `[boardId]` before `search.get.ts`, rename to `boards-search.get.ts` and update the `$fetch` call.

3. **MC answer grading is exact-match** — fragile for longer correct answers.

4. **board_embedding centroid computation** — runs synchronously in the pipeline after embedding. For large boards (50+ sources × 50+ chunks each) this is a multi-second DB average computation inline in the worker. Move to a background task or rate-limit per board in M5.

---

## Architectural Invariants (don't break these)

| Invariant | Where | Why |
|---|---|---|
| `CREATE EXTENSION vector` before `chunks` table | Migration 001 | pgvector requires this |
| Each fork gets its own KB via `KnowledgeBaseService.create()` | `curation/service.py` fork_board | Per-fork namespace isolation; `get_or_create_default` was the bug |
| Dedup keyed on `(content_hash, source_id)` | `worker/pipeline.py _dedup()` | New source_id in fork → fresh chunks with correct namespace |
| SSE format: `event: citations` first, then bare `data:` tokens | `citations.py` | Must match `useStreamingQuery.ts` |
| `RetrievedChunk` / `ConceptProposal` / `build_fork_lineage` in pure `types.py` | Import structure | Keeps tests free of FastAPI/SQLAlchemy imports |
| `_ollama_generate` is a module-level wrapper in `agent.py` | Test patchability | Deferred import so agent.py loads without httpx |
| Alembic uses `DATABASE_SYNC_URL` | `alembic/env.py` | asyncpg driver not usable by Alembic sync ops |
