# Roadmap — Knowledge Comms

**Status:** Pre-development planning artifact  
**Version:** 0.1

---

## MVP Philosophy

The MVP must prove the platform's core thesis: that a grounded corpus can be automatically transformed into a structured, assessable, citable experience — and that this is qualitatively different from anything assembled manually or from an LLM with no grounding.

**The grounding is not a polish feature. It is the product.** An MVP that strips out attribution to ship faster does not demonstrate the thesis.

Every MVP mechanic is designed to be upgradable to the full-build mechanic without breaking schema migrations on user data.

---

## MVP Scope

### Layer 1 — Grounded Knowledge Core (MVP)

| Capability | MVP | Notes |
|---|---|---|
| PDF ingestion + chunking | YES | Core thesis requirement |
| Web page ingestion | YES | URL paste |
| Video transcript ingestion | NO — V2 | Audio transcription is long-running; adds ingestion complexity |
| Image OCR | NO — V2 | |
| Semantic chunking + embedding | YES | Core thesis requirement |
| Vector storage with namespace isolation | YES | Multi-tenant isolation is a safety invariant, not a feature |
| Grounded Q&A with citations | YES | Core thesis requirement |
| Hybrid retrieval (dense + sparse) | NO — simplified | MVP: dense-only with BM25 fallback; full re-ranking post-MVP |
| Multi-hop synthesis agents | NO — V2 | MVP: single-hop Q&A |
| Knowledge graph overlay | NO — V2 | |
| Source fidelity scoring | Partial | Simple drift detection; full eval harness post-MVP |
| Model version tracking per KB | YES | Architectural invariant; cheap to include at inception |

### Layer 2 — Structured Learning Layer (MVP)

| Capability | MVP | Notes |
|---|---|---|
| AI curriculum proposal from a corpus | YES | Core thesis requirement |
| Grounded concept explanations with inline citations | YES | Core thesis requirement |
| Prerequisite graph inference | NO — V2 | MVP: flat linear sequence |
| MC assessment with grounded distractors | YES | Core thesis requirement |
| Open-ended assessment with rubric | NO — V2 | Requires reliable OE verification pipeline |
| Source retrieval question type | NO — V2 | |
| Instructor review and override interface | YES | Core thesis requirement |
| Spaced repetition scheduling | NO — simplified | MVP: simple fixed-interval review (1d, 3d, 7d, 14d) |
| Mastery gates | NO — soft only | Surface score without blocking at MVP |
| Cohort enrollment | NO — V2 | MVP: single-learner only |
| Passage-anchored discussion | NO — V2 | Requires cohort |
| Comprehension heatmaps | NO — V2 | Requires cohort |
| Corpus change propagation / staleness | NO — V2 | Requires event infrastructure |
| Learning path versioning | NO — V2 | Single version at MVP |

### Layer 3 — Discovery and Curation Layer (MVP)

| Capability | MVP | Notes |
|---|---|---|
| Public board view (swim-lane layout) | YES | Core thesis requires the fork loop |
| Rich media cards (PDF, web) | YES | |
| Fork action with ingestion progress | YES | Core loop demonstrator |
| Fork attribution (one level deep) | YES | |
| URL paste entry point | YES | |
| PDF upload | YES | |
| AI-generated board summary | YES | Shown on public board; drives discoverability |
| Semantic board recommendations | YES | Core differentiator; must be real at launch |
| Curator profiles | YES | Basic: boards published + inferred expertise |
| Cross-collection semantic search | YES | Single-query, centroid-based |
| Trending collections | Simplified | Fork-count ranking + quality floor; no full weighted scoring |
| Curator following and feed | NO — V2 | |
| Grounded comments on source cards | NO — V2 | |
| Free-form canvas mode | NO — V2 | MVP: swim-lane only |
| Team-shared boards | NO — V2 | |
| Mobile capture (photo → OCR) | NO — V2 | |
| Batch import | NO — V2 | |
| Human moderation queue | NO — V2 | |
| Gap analysis | Simplified | Source-type balance only; perspective gap detection post-MVP |
| Opt-in fork sync | NO — V2 | |

### Cross-Cutting (MVP)

| Capability | MVP | Notes |
|---|---|---|
| Private / public visibility | YES | |
| Single-user auth (email + password + social OAuth) | YES | |
| Team workspaces | NO — V2 | |
| Developer API | NO — V2 | |
| Webhooks | NO — V2 | |
| Browser extension | NO — V2 | MVP: URL paste on board |
| Cost attribution and usage dashboard | Internal only | Operators need it; user-facing post-MVP |

---

## MVP Success Criteria

The MVP is successful when:

1. A user can upload 5 PDFs and ask a question that gets a cited, grounded answer within 5 minutes of their first visit
2. The AI can propose a learning path from those 5 PDFs with concept explanations that each cite at least one source passage
3. A user can browse a public board, understand its scope from the board summary and card previews, fork it, and have an active queryable knowledge base within 10 minutes
4. Grounded assessment feedback cites the specific source passage that clarifies a wrong answer — for every wrong answer, not just some

---

## V2 Priorities (Post-MVP)

Ordered by expected user impact:

1. **Cohort learning** — Unlocks the instructor persona fully; passage-anchored discussion, comprehension analytics, mastery gates
2. **Video/audio ingestion** — Transcript extraction with timestamp locators; dramatically expands addressable source types
3. **Multi-hop synthesis agents** — "Compare these three sources on topic X" with multi-document citation
4. **Team workspaces** — Collaborative knowledge bases for professional teams
5. **Browser extension** — Reduces friction for web content capture
6. **Prerequisite graph** — Non-linear learning paths; enables branching, adaptive pacing
7. **Open-ended assessment with grounded rubric** — Higher-fidelity comprehension checking
8. **Fork sync notifications** — Community loop: updates propagate to fork owners
9. **Knowledge graph overlay** — Entity-relationship layer over the corpus for enhanced discovery
10. **Developer API + webhooks** — Third-party integrations; custom ingestion adapters

---

## Technical Milestones

### Milestone 0 — Infrastructure Baseline (Week 1–2)
- Docker Compose stack: all services in one `compose.yml`
- PostgreSQL + pgvector schema (Source, Chunk, KnowledgeBase, Collection, User)
- Ollama container with default model pre-pulled and warm
- MinIO container for object storage (or local bind-mount for single-user)
- Redis Streams as the message queue for async ingestion jobs
- Nginx reverse proxy with TLS (Let's Encrypt)
- Auth: JWT issuance, session management (no external auth provider)

### Milestone 1 — Ingestion Loop (Week 3–4)
- PDF ingestion: parse → chunk → embed → vector store
- Web page ingestion: scrape → extract → chunk → embed
- Ingestion job status + WebSocket progress updates
- Source deduplication (content hash)
- Grounded Q&A against a single knowledge base

### Milestone 2 — Core AI Flows (Week 5–7)
- Curriculum agent: concept extraction, flat sequence, explanation generation
- Assessment generation: MC questions with grounded distractors
- Instructor review interface: accept / override / prune concepts
- Learner-facing path: read explanations, attempt assessment, see grounded feedback

### Milestone 3 — Discovery Surface (Week 8–10)
- Collection boards: swim-lane layout, source cards
- Fork action: copy sources, trigger ingestion, activate AI core
- Public board profiles with AI-generated summaries
- Semantic recommendation engine (centroid search against public board index)
- Curator profiles

### Milestone 4 — MVP Hardening (Week 11–12)
- Multi-tenant isolation audit (verify namespace filtering is airtight)
- Source fidelity check on all Q&A responses
- Basic rate limiting and cost tracking
- Production deployment, monitoring, alerting

---

## Cost Model Notes

**Zero software licensing cost.** Every component is open-source and self-hosted. There are no per-token, per-query, or per-user charges at any scale.

**Hardware cost only:**
- Minimum viable (personal/small team): repurposed hardware or a Hetzner VPS (~€5–50/month)
- Recommended production (community): dedicated server with NVIDIA GPU (~€50–200/month)
- There is no free tier design needed: the operator sets resource quotas based on available hardware, not per-query billing math

**Scaling note:** pgvector handles hundreds of users comfortably on a 32–64GB RAM host. Migration to self-hosted Qdrant is the defined path when the vector index exceeds available RAM (~1,000+ active users with large corpora). Embedding model migration is an overnight background job on GPU, or a multi-night background job on CPU-only.
