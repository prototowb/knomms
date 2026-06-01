<!-- proto-gear:header
purpose: Project planning document — source for architecture and product decisions
read-when: Starting features or design work; first session on a new domain
priority: required-if-exists
defines:
  - platform-vision
  - tech-stack
  - layer-architecture
  - mvp-scope
  - ai-principles
links:
  - PROJECT_STATUS.md
  - AGENTS.md
  - docs/00-vision.md
  - docs/01-product-spec.md
  - docs/02-ai-architecture.md
  - docs/03-learning-layer.md
  - docs/04-discovery-layer.md
  - docs/05-platform-architecture.md
  - docs/06-roadmap.md
  - docs/07-frontend-architecture.md
  - docs/08-backend-architecture.md
-->

# PROJECT_SPECIFICATIONS.md — Knowledge Commons

> **Entry point for all architectural and product decisions.**
> This document is the index. The detailed specs live in `docs/`. An agent reading this file has enough context to orient and knows exactly where to go deeper.

---

## What This Is

**Knowledge Commons** is a grounded collective intelligence platform: a self-hosted, zero-external-cost system where individuals and communities build, share, and learn from AI-powered knowledge bases.

The AI is not a feature layer on top of content management — it **is** the content model. Every source (document, video, web page, audio) becomes a queryable, citable semantic corpus. Every AI output is anchored to specific source passages with attribution. No free-floating generation.

---

## Three-Layer Architecture

| Layer | Role | Deep-dive |
|---|---|---|
| **Grounded Knowledge Core** | Multimodal ingestion → semantic chunks → RAG with citations → agentic synthesis | `docs/02-ai-architecture.md` |
| **Structured Learning Layer** | AI transformation agent: corpus → learning paths + assessments | `docs/03-learning-layer.md` |
| **Discovery & Curation Layer** | Visual collection boards; fork → activates Knowledge Core | `docs/04-discovery-layer.md` |

Community (co-authorship, grounded discussion, fork lineage) permeates all three layers.

---

## Tech Stack

| Concern | Technology | Notes |
|---|---|---|
| Frontend | Vue 3 + Nuxt 3 + Tailwind CSS + Pinia | Hybrid SSR (public boards) + SPA (app) |
| Backend API | Python 3.12 + FastAPI | Modular monolith; `app/` + `worker/` |
| AI inference | Ollama (local) | Mistral 7B / Llama 3 / Phi-3 by hardware tier |
| Embeddings | nomic-embed-text-v1.5 via Ollama | Apache 2.0; zero egress |
| Agent orchestration | LangGraph + PostgreSQL checkpoints | Synthesis, Curriculum, Assessment agents |
| Database | PostgreSQL 16 + pgvector | Relational data + vector index in one service |
| Object storage | MinIO (self-hosted, S3-compatible) | Raw media; served via Nginx signed URLs |
| Cache / queue | Redis 7 + Redis Streams | Cache, pub/sub presence, ingestion job queue |
| Reverse proxy | Nginx | TLS termination, static assets, SSE proxy |
| Deployment | Docker Compose | Single-host; no managed cloud dependencies |

Full deployment reference: `docker-compose.yml`

---

## AI Architecture Principles (non-negotiable)

1. **Retrieval before generation** — No output without a grounded retrieval step
2. **Attribution as data** — Citation/provenance is a first-class field, not a footnote
3. **Multimodal parity** — PDF, web, video transcripts, images, audio are equal citizens
4. **Agentic, not just Q&A** — AI proposes learning paths, synthesizes, generates assessments
5. **Evals baked in** — NLI fidelity scorer on every generation; source fidelity < 0.8 triggers warning or block
6. **Privacy by default** — KBs private until published; no training on user content without opt-in
7. **Self-hostable, zero external cost** — Runs on Docker Compose; no API keys, no SaaS subscriptions

---

## Core Data Model (condensed)

```
Source → Chunk (text + embedding + locator)
                ↓ contained in
Collection (visual board) → KnowledgeBase (vector namespace)
                                    ↓ generates
                             LearningPath → Module → Citation → Chunk
```

Every `Citation` is a first-class persisted record linking a `Module` to a `Chunk` with a verbatim quote. This is the grounding contract enforced at the database layer.

Full ER sketch and schemas: `docs/05-platform-architecture.md` §2

---

## MVP Scope (what ships first)

**The MVP proves one thesis: a grounded corpus automatically becomes a structured, assessable, citable learning experience.**

MVP includes:
- PDF + web URL ingestion → chunking → pgvector embedding
- Grounded Q&A with SSE streaming and citation side panel
- AI curriculum proposal (flat sequence) from a corpus
- MC assessment with grounded distractor rationale
- Instructor review + override interface
- Collection boards (swim-lane layout) + fork action
- Public board view (SSR) + curator profiles
- Semantic board recommendations (embedding-based, not collaborative filtering)
- JWT auth, Docker Compose single-host deployment

Full scope table per layer: `docs/06-roadmap.md`

---

## Document Map

| Document | Read when |
|---|---|
| `docs/00-vision.md` | Understanding the platform thesis and design bets |
| `docs/01-product-spec.md` | Personas, capabilities, user journeys, non-goals |
| `docs/02-ai-architecture.md` | Ingestion pipeline, embeddings, RAG, agents, guardrails |
| `docs/03-learning-layer.md` | Curriculum agent, data model, assessment, spaced repetition |
| `docs/04-discovery-layer.md` | Board UI, fork mechanic, semantic recommendations |
| `docs/05-platform-architecture.md` | Service decomposition, data models, auth, search, cost model |
| `docs/06-roadmap.md` | MVP scope tables, technical milestones, hardware sizing |
| `docs/07-frontend-architecture.md` | Vue 3/Nuxt 3 structure, Tailwind config, streaming patterns |
| `docs/08-backend-architecture.md` | FastAPI structure, SQLAlchemy, Ollama client, worker, testing |
| `docker-compose.yml` | Full self-hosted deployment stack |

---

## Key Design Decisions (with rationale)

| Decision | Choice | Why |
|---|---|---|
| LLM inference | Ollama (local) | Zero cost; full data sovereignty; no API key |
| Embedding model | nomic-embed-text-v1.5 | Apache 2.0; 8192-token context; competitive quality |
| Vector DB | pgvector (MVP) → Qdrant (>20M chunks) | Operational simplicity; single DB for relational + vector |
| Agent framework | LangGraph | Inspectable graph topology; built-in HITL checkpointing |
| Deployment | Docker Compose | Self-hosted; no Kubernetes overhead at this scale |
| Frontend | Vue 3 + Nuxt 3 | Hybrid SSR/SPA; Vue reactivity suits real-time features |
| CSS methodology | Tailwind CSS | Co-location; no cascade to model; AI-readable |
| Backend architecture | Modular monolith | One FastAPI app + one worker; 7 domains as Python packages |
| Message queue | Redis Streams | Already running Redis; avoids a separate service |
| Object storage | MinIO | S3-compatible; self-hosted; free |

---

## Open Questions (unresolved design decisions)

1. **Paywall sources:** Handle articles behind paywalls as excerpt-only, user-provided full text, or blocked?
2. **Multimodal image reasoning depth:** OCR + caption at MVP; full chart/diagram interpretation in V2 — which model?
3. **Sensitive/confidential corpora:** Isolated vector namespace with network-level separation for enterprise; when does this tier ship?
4. **API model exposure:** Expose Ollama model selection to power users or lock to operator-configured default?
5. **Content moderation at scale:** Human moderation queue design for public boards (V2 — not in MVP)

---

## Project State

See `PROJECT_STATUS.md` for current sprint, active tickets, and what's in progress.
Pre-development as of 2026-06-01. All `docs/` are specification-level artifacts. No production code exists yet.
