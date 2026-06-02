# Changelog

All notable changes to Knowledge Commons are documented here.

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
