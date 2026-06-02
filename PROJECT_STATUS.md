# PROJECT STATUS — Knowledge Comms

> **Single Source of Truth** for project state. Read this first every session.

## Hand-off — start here

**What this is.** A self-hosted, zero-external-cost grounded collective intelligence platform. Three layers: AI knowledge core (RAG + agents), structured learning (AI-generated learning paths from corpora), and discovery/curation (visual collection boards with fork-to-KB mechanic). Full specification in `PROJECT_SPECIFICATIONS.md`.

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
project_phase: "Active development — Milestones 0–4 complete + post-MVP hardening"
protogear_enabled: true
framework: "Vue 3 + Nuxt 3 (frontend) / Python 3.12 + FastAPI (backend)"
project_type: "Self-hosted web application"
initialization_date: "2026-06-01"
current_sprint: "MVP Launch Prep"
last_release: "v0.1.0 (2026-06-02)"
ticket_prefix: "KC"
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

## 🎫 Active — Post-MVP Hardening

*All three layers live and verified. GitHub remote configured (prototowb/knomms). Workflow: feature branches → development (local merge + push); development → main via PR.*

Next candidates (see SESSION_HANDOFF.md §What Comes Next):
- KC-030: Async board summary — add background job if prompt size grows with multi-source boards
- KC-031: `development` → `main` release PR — tag v0.1.0

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
