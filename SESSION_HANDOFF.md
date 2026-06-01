# Session Handoff — Knowledge Commons

**Session date:** 2026-06-01  
**Ended at:** Milestone 2 complete  
**Branch:** `main` — all work committed directly  
**Tests:** 55/55 passing (chunker, citations, learning agent)

---

## What This Project Is

A self-hosted, zero-external-cost grounded collective intelligence platform. Three layers:
1. **Knowledge Core** — multimodal ingestion → RAG with citations → agentic synthesis
2. **Learning Layer** — AI-generated learning paths + assessments from a corpus
3. **Discovery Layer** — visual collection boards; fork → activates Knowledge Core

Full specification: `PROJECT_SPECIFICATIONS.md` → `docs/` for deep-dives.  
Tech stack summary: `README.md`.

---

## What Was Built (Cumulative)

### Milestone 0 — Infrastructure Baseline (commit `6bb3ef6`)
Docker Compose stack, env, nginx, backend Dockerfile, pyproject.toml, core modules, ORM models (User/Source/Chunk/KnowledgeBase/Collection), Alembic migration 001 (pgvector + 5 tables), identity domain (register/login/refresh/me), Nuxt 3 frontend scaffold (Tailwind, Pinia auth store, SSE composable, BFF routes).

### Milestone 1 — Ingestion Loop + Grounded Q&A (commit `cbb34da`)
Migration 002 (vector_namespace on chunks), ingestion domain (RawBlock, PDF/web extractors, semantic chunker, service, router), retrieval domain (pgvector cosine search, namespace-scoped), generation domain (Ollama client, citation injection/validation, SSE streaming router), Redis Streams worker (7-stage ingestion pipeline, batched embedding). 29 unit tests.

### Milestone 2 — Core AI Flows (commit `bcfb0b4`)

**Three pre-code decisions made:**
1. **No LangGraph** — MVP pipeline is strictly linear (group → explain → assess), so plain async Python + existing Ollama client is simpler. LangGraph earns its weight on stateful/branching graphs; this isn't one yet.
2. **No semantic clustering** — spec §8.3 explicitly permits heading-heuristic grouping at MVP. `_extract_heading()` splits chunks on the `"Heading\n\nBody"` format the chunker already emits.
3. **Grounding enforced at the agent layer** — `generate_concept_proposal()` discards any proposal where all cited IDs are hallucinated (not in the passage group). The data layer (JSONB + application FK) stores the result; the agent is the validation gate.

| New file | Purpose |
|---|---|
| `alembic/versions/003_learning_layer.py` | 4 new tables: learning_paths, path_concepts, assessment_items, distractors |
| `app/models/learning.py` | ORM models for the 4 learning tables |
| `app/domains/learning/types.py` | Pure dataclasses: PassageDraft, ConceptProposal, AssessmentDraft, DistractorDraft |
| `app/domains/learning/agent.py` | `build_concept_groups`, `generate_concept_proposal`, `generate_curriculum` |
| `app/domains/learning/service.py` | `LearningService`: create_draft, get_path, list_paths, update_concept, publish_path, grade_attempt |
| `app/schemas/learning.py` | Pydantic v2 request/response schemas |
| `app/domains/learning/router.py` | 6 endpoints (see below) |
| `app/main.py` | +learning router registration |
| `tests/test_learning_agent.py` | 26 tests — heading extraction, grouping, JSON parsing, proposal generation (mocked) |
| `frontend/pages/kb/[kbId]/index.vue` | **Rewritten** — real Q&A UI with citation sidebar + link to learning paths |
| `frontend/pages/kb/[kbId]/learn/index.vue` | Learning paths list + generate-new-path form |
| `frontend/pages/learn/[pathId]/index.vue` | Learning path view: concept nav, explanation, source passages toggle, MC assessment, accept/prune instructor controls |
| `frontend/composables/useStreamingQuery.ts` | **Fixed** — query now passed to `submit(query)`, not captured at init |
| `frontend/server/api/kb/[kbId]/learning-paths.{get,post}.ts` | BFF list + create |
| `frontend/server/api/learning-paths/[pathId]/*` | BFF get, publish, patch concept, attempt |

**API endpoints added:**
- `POST /v1/kbs/{kb_id}/learning-paths` — generate curriculum from corpus
- `GET /v1/kbs/{kb_id}/learning-paths` — list paths for KB
- `GET /v1/learning-paths/{path_id}` — full path with concepts + assessments
- `PATCH /v1/learning-paths/{path_id}/concepts/{concept_id}` — accept/prune/annotate
- `POST /v1/learning-paths/{path_id}/publish` — publish draft
- `POST /v1/learning-paths/{path_id}/concepts/{concept_id}/items/{item_id}/attempt` — MC answer grading

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
│   │   └── 003_learning_layer.py          ← M2
│   ├── app/
│   │   ├── main.py
│   │   ├── core/               ← config, db, redis, security
│   │   ├── deps/               ← get_db, get_current_user
│   │   ├── models/             ← User, Source, Chunk, KB, Collection, Learning ✓ M2
│   │   ├── schemas/            ← user, source, kb, learning ✓ M2
│   │   ├── domains/
│   │   │   ├── identity/       ← ✓ M0
│   │   │   ├── knowledge_base/ ← ✓ M1
│   │   │   ├── ingestion/      ← ✓ M1
│   │   │   ├── retrieval/      ← ✓ M1
│   │   │   ├── generation/     ← ✓ M1
│   │   │   └── learning/       ← agent, service, router, types ✓ M2
│   │   └── worker/             ← ✓ M1
│   └── tests/
│       ├── test_chunker.py     ← 13 tests ✓
│       ├── test_citations.py   ← 16 tests ✓
│       └── test_learning_agent.py ← 26 tests ✓ M2
└── frontend/
    ├── Dockerfile
    ├── nuxt.config.ts
    ├── tailwind.config.ts
    ├── stores/auth.ts
    ├── composables/
    │   └── useStreamingQuery.ts ← fixed in M2
    ├── pages/
    │   ├── index.vue
    │   ├── explore/index.vue
    │   ├── kb/[kbId]/
    │   │   ├── index.vue        ← real Q&A UI ✓ M2
    │   │   └── learn/index.vue  ← path list ✓ M2
    │   └── learn/[pathId]/
    │       └── index.vue        ← path detail ✓ M2
    └── server/api/
        ├── auth/
        └── kb/[kbId]/ + learning-paths/[pathId]/ ← BFF routes ✓ M2
```

---

## Known Issues / Caveats

1. **Docker not verified.** Docker was unavailable in the dev environment for both M1 and M2. All code is syntax-clean and unit-tested on pure logic, but the full stack requires Docker for integration verification. The first real run will surface integration issues.

2. **`SourceOut.kb_id` is set post-validation** (M1 carryover). In `ingestion/router.py`, `kb_id` is set on the Pydantic model after `model_validate()`. Fragile — should be passed through the source model or as a dedicated schema.

3. **Upload bytes held in Redis (TTL 1 hour)** (M1 carryover). Large files (up to 200MB) bloat Redis memory. For M3, move to a MinIO presigned-URL upload flow.

4. **Chunker sentence splitter is punctuation-dependent** (M1 carryover). Lists, table cells, and code stay as one big "sentence". A word-boundary fallback should be added.

5. **Curriculum agent is sequential.** `generate_curriculum()` calls Ollama one concept group at a time to avoid overloading the single Ollama instance. For corpora with many sections (20+ groups), this will be slow. M3 can add a semaphore-bounded concurrent queue if needed.

6. **MC answer grading is exact-match.** `grade_attempt()` compares `answer.strip().lower()` against `correct_answer.strip().lower()`. For longer answers this is fragile. A fuzzy-match or substring approach should replace it when the UI exposes free-text entry (currently the frontend only allows selecting the exact distractor text).

7. **Learning paths list doesn't load concept counts.** `list_paths()` returns paths without eagerly loading `concepts`, so `concept_count` is always 0 in the summary. Fix: add a `COUNT` subquery or load with `selectinload` and count in Python.

---

## What Comes Next — Milestone 3

From `docs/06-roadmap.md`:

> **Milestone 3 — Discovery Surface**
> - Public board view: swim-lane layout (SSR)
> - Fork action with ingestion progress
> - Curator profiles
> - Semantic board recommendations

**The three things to resolve before writing M3 code:**

1. **Collection/board data model gap.** Migration 001 has `Collection` and `CollectionItem` but no `Board` entity or `fork` tracking. The discovery spec (`docs/04-discovery-layer.md`) defines `Board → CollectionItem[] → Source`. Clarify if `Collection` IS the board or if a `Board` wraps `Collection`.

2. **Public SSR.** `pages/explore/index.vue` is a stub. M3 needs `routeRules` entries for SSR public routes (`/board/[boardId]`, `/u/[handle]`) and server-side data fetching via `useFetch`.

3. **Semantic recommendations.** The spec requires cross-collection vector similarity (centroid-based). This reuses the pgvector embed + retrieve infrastructure from M1 but adds a `collections` embedding column and a batch re-embed job triggered on collection update.

**Suggested M3 ticket sequence:**
```
KC-019  Migration 004 — Board entity, fork tracking, board_embedding column
KC-020  Board service — create, fork, get public board
KC-021  Board SSR page — public swim-lane view (/board/[boardId])
KC-022  Fork action — UI + ingestion trigger + progress
KC-023  Curator profile page (/u/[handle])
KC-024  Semantic recommendation service — centroid embed + cosine board search
KC-025  Explore page — trending + recommended boards
```

---

## Architectural Invariants (don't break these)

| Invariant | Where enforced | Why |
|---|---|---|
| `CREATE EXTENSION vector` before `chunks` table | Migration 001 ordering | pgvector fails without the extension |
| `Chunk.vector_namespace` stamped at ingest time | `pipeline.py` + `chunker.py` | Enables single-WHERE retrieval |
| KB auth = ownership check, not JWT namespaces | `generation/service.py`, `kb/service.py` | JWT namespaces only populated at login |
| SSE format: `event: citations` first, then bare `data:` tokens | `citations.py` | Must match `useStreamingQuery.ts` frontend contract |
| `RetrievedChunk` lives in `retrieval/types.py` | Import structure | Keeps citation tests free of SQLAlchemy |
| `ConceptProposal` / `PassageDraft` live in `learning/types.py` | Import structure | Keeps learning agent tests free of SQLAlchemy |
| `_ollama_generate` is a module-level wrapper in `agent.py` | Test patchability | Deferred import so agent.py loads without httpx |
| Alembic uses `DATABASE_SYNC_URL` | `alembic/env.py` | `DATABASE_URL` uses asyncpg; Alembic needs sync driver |

---

## How to Re-orient in a New Session

```bash
# 1. Read project state
cat PROJECT_STATUS.md

# 2. Confirm tests still pass
cd backend && python3 -m pytest tests/ -q

# 3. See what's committed
git log --oneline -10

# 4. Check for any uncommitted work
git status
```
