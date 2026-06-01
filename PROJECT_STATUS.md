# PROJECT STATUS — Knowledge Commons

> **Single Source of Truth** for project state. Read this first every session.

## Hand-off — start here

**What this is.** A self-hosted, zero-external-cost grounded collective intelligence platform. Three layers: AI knowledge core (RAG + agents), structured learning (AI-generated learning paths from corpora), and discovery/curation (visual collection boards with fork-to-KB mechanic). Full specification in `PROJECT_SPECIFICATIONS.md`.

**Where we are.** Pre-development. All `docs/` contain specification-level artifacts (vision, product spec, AI architecture, layer specs, platform architecture, roadmap, frontend + backend architecture). No production code exists yet.

**Read in this order:**

1. This file → current state and open tickets
2. `PROJECT_SPECIFICATIONS.md` → platform overview, tech stack, document map
3. `AGENTS.md` → agent orchestration and pre-flight checklist
4. Relevant `docs/` → deep-dive specs per domain (see document map in PROJECT_SPECIFICATIONS.md)
5. `BRANCHING.md` / `TESTING.md` → conventions before any git or test work

**To run (once code exists):**

```bash
cp .env.example .env    # set POSTGRES_PASSWORD, SECRET_KEY, MINIO_ROOT_PASSWORD
docker compose up -d
docker compose exec api python manage.py migrate
# Frontend: http://localhost  Backend API: http://localhost/api
```

---

## Current State

```yaml
project_phase: "Pre-development — specification complete"
protogear_enabled: true
framework: "Vue 3 + Nuxt 3 (frontend) / Python 3.12 + FastAPI (backend)"
project_type: "Self-hosted web application"
initialization_date: "2026-06-01"
current_sprint: null
last_release: null
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

## 🎫 Active Tickets

*No active tickets — project is in pre-development specification phase.*

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

## Suggested First Tickets (when development begins)

Create these with `pg ticket create "title" --type feature`:

**Milestone 0 — Infrastructure Baseline**
- Docker Compose stack: db, redis, minio, ollama, nginx services
- PostgreSQL schema + pgvector extension + Alembic baseline migration
- FastAPI app skeleton: settings, db dependency, JWT auth endpoints

**Milestone 1 — Ingestion Loop**
- PDF ingestion pipeline: extract → chunk → embed → pgvector
- Web URL ingestion: Playwright scrape → chunk → embed
- Grounded Q&A endpoint with SSE streaming + citation format

**Milestone 2 — Core AI Flows**
- Curriculum agent: LangGraph, flat sequence, MC assessment generation
- Instructor review interface (accept / override / prune concepts)

**Milestone 3 — Discovery Surface**
- Nuxt 3 frontend: collection boards + fork action
- Public board view (SSR) + curator profiles
- Semantic recommendation engine

See `docs/06-roadmap.md` for full milestone breakdown and MVP scope tables.

---

## Recent Updates

- 2026-06-01: Full project specification complete (9 architecture docs)
- 2026-06-01: Proto Gear agent framework initialized

---

*Maintained by Proto Gear Agent Framework*
