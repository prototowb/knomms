# Knowledge Commons

A grounded collective intelligence platform where communities build, share, and learn from AI-powered knowledge bases.

## What It Is

Knowledge Commons combines three layers into a single coherent product:

- **Grounded Knowledge Core** — Any collection of sources (documents, video, images, web pages) becomes a queryable, citable knowledge base. Every AI output is anchored to specific source passages with attribution.
- **Structured Learning Layer** — An AI transformation agent that turns a corpus into learning paths, assessments, and cohort experiences — all citations traceable back to source.
- **Discovery and Curation Layer** — Visual collection boards that anyone can browse, fork, and convert into their own knowledge base.

Community (co-authorship, grounded discussion, fork lineage) permeates all three layers.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/00-vision.md`](docs/00-vision.md) | Platform thesis and design principles |
| [`docs/01-product-spec.md`](docs/01-product-spec.md) | Personas, capabilities, user journeys |
| [`docs/02-ai-architecture.md`](docs/02-ai-architecture.md) | Layer 1 — Grounded Knowledge Core (AI/ML architecture) |
| [`docs/03-learning-layer.md`](docs/03-learning-layer.md) | Layer 2 — Structured Learning Layer (product + technical) |
| [`docs/04-discovery-layer.md`](docs/04-discovery-layer.md) | Layer 3 — Discovery and Curation Layer (product) |
| [`docs/05-platform-architecture.md`](docs/05-platform-architecture.md) | Cross-cutting platform, data models, infrastructure |
| [`docs/06-roadmap.md`](docs/06-roadmap.md) | MVP scope, phasing, and full-build roadmap |
| [`docs/07-frontend-architecture.md`](docs/07-frontend-architecture.md) | Frontend stack, project structure, interaction patterns |
| [`docs/08-backend-architecture.md`](docs/08-backend-architecture.md) | Python/FastAPI layer, domain structure, worker, auth, testing |

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 + Nuxt 3 (hybrid SSR/SPA) + Tailwind CSS + Pinia |
| Backend API | Python (FastAPI) |
| AI inference | Ollama (local LLM — Mistral/Llama 3/Phi-3) |
| Embeddings | nomic-embed-text-v1.5 (via Ollama) |
| Database | PostgreSQL 16 + pgvector |
| Object storage | MinIO (S3-compatible, self-hosted) |
| Cache / queue | Redis 7 + Redis Streams |
| Reverse proxy | Nginx |
| Deployment | Docker Compose |

## Core Design Principles

1. **Retrieval before generation** — No AI output without a grounding retrieval step
2. **Attribution as data** — Citation/provenance is a first-class field, not a footnote
3. **Multimodal parity** — Text, images, audio/video, and structured data are equal citizens
4. **Agentic, not just Q&A** — AI proposes, compiles, compares, generates learning paths
5. **Evals baked in** — Source fidelity scoring and human-feedback loops from day one
6. **Privacy by default** — Knowledge bases are private until explicitly published

## Project Status

Pre-development. All documents in this repo are specification-level artifacts generated during the initial architecture planning phase. No production code exists yet.

See [`docs/06-roadmap.md`](docs/06-roadmap.md) for MVP scope.
