# Knowledge Comms — Platform and Data Architecture

## Cross-Cutting Technical Specification v0.1

**Audience:** Engineering leads, backend architects, infrastructure/SRE

---

## 1. Overall System Architecture

### Service Decomposition

Knowledge Comms decomposes into seven bounded domains:

**Ingestion Service** — owns the full lifecycle from URL/upload submission through parsing, chunking, embedding, and index population. Entirely async after the initial submission endpoint. The domain entity is `Source` + `Chunk`.

**Retrieval Service** — the query-time engine: holds the vector index, executes hybrid retrieval, returns `Chunk` results with provenance. Read-heavy and stateless at request time. Knows nothing about who a user is beyond a resolved set of `namespace_ids` handed by the API gateway after auth. Multi-tenant isolation is enforced here.

**Generation Service** — wraps all LLM API calls. Accepts a prompt template, a list of `Chunk` references (from Retrieval), and generation parameters. Returns a structured completion with citation anchors mapped back to input Chunk IDs. Never generates without retrieved context — ungrounded output is a failure mode the service refuses to produce.

**Learning Service** — manages `LearningPath`, `Module`, `Assessment`, and `Enrollment` entities. Calls Retrieval and Generation for curriculum generation. Background jobs here are long-running.

**Curation Service** — manages `Collection`, `Board`, `BoardItem`, and fork/lineage state. Collaborative presence and concurrent edit conflict resolution live here.

**Identity Service** — owns users, organizations, team memberships, follow graphs, and API keys. Issues JWTs. Upstream of everything.

**Notification Service** — subscribes to the event stream from all other services and fans out to delivery channels (email, push, in-app feed, webhook). Owns no domain data.

### Deployment Model

**Self-hosted, Docker Compose.** The platform is designed to run on a single machine (bare metal, VPS, or local server) using Docker Compose. There are no managed cloud service dependencies. The entire platform — including AI inference, databases, storage, and message queue — runs in containers on the host machine.

**Minimum viable hardware:** 16GB RAM, 4 CPU cores, 50GB disk. No GPU required, but inference throughput is significantly reduced on CPU-only hardware (see `docs/02-ai-architecture.md` §3.5 for model tier guidance).

**Recommended production hardware:** 32GB RAM, 8 CPU cores, 500GB NVMe SSD, NVIDIA GPU with 12–24GB VRAM (RTX 3090, RTX 4090, or equivalent). Total hardware cost: ~$1,000–$2,500 for a new build; near-zero for repurposed server hardware. VPS option: Hetzner AX41 (~€35/month) for CPU-only or a GPU cloud instance for inference-heavy workloads.

A Kubernetes-based deployment is possible for multi-node scaling (the service architecture supports it), but it is not the default and not required at any scale this platform is likely to reach in its first 1–2 years.

Storage (all self-hosted, zero software licensing cost):
- **PostgreSQL + pgvector** — all transactional data AND vector embeddings in the same database instance; row-level security for multi-tenant isolation
- **MinIO** — S3-compatible object storage for raw media files (PDFs, video, images) and derived assets, running as a Docker container on the same host; falls back to local filesystem bind-mount for single-user deployments
- **Redis** — cache, rate-limit counters, session state, pub/sub fan-out (open source, Docker container)
- **Redis Streams** — serves as the message queue for async ingestion jobs; eliminates the need for a separate queue service at MVP scale

### API Gateway and BFF Pattern

A single API gateway handles TLS termination, JWT validation, rate limiting, and routing. It injects an enriched request envelope (`user_id`, `org_id`, resolved `namespace_ids`) as trusted internal headers. No downstream service re-validates the JWT.

Three BFF (backend-for-frontend) services:
- **Web BFF** — composes calls across Retrieval, Curation, and Learning for page-level data shapes; manages WebSocket connections for real-time presence and progress
- **Mobile BFF** — thinner, tighter payload budgets, offline-first pagination cursors, push notification registration
- **Extension BFF** — lowest latency budget; exposes only ingestion submission and quick search

### Async vs Sync Boundaries

**Must be synchronous (< 500ms p95):**
- Source submission receipt (return job ID, acknowledge immediately)
- Q&A / chat queries
- Search results
- Board loading and item manipulation
- Authentication and token issuance

**Eventual consistency acceptable (seconds to minutes):**
- Ingestion completion and index population (WebSocket progress, not polling)
- Embedding regeneration after model version migration
- Follow/fork notifications
- Curriculum generation

**Guaranteed delivery, never blocking:**
- Notification fan-out
- Webhook delivery
- Search index updates after source deletion or visibility change

---

## 2. Core Data Models

### Entity-Relationship Sketch

```
User ─────────── owns ───────────────────► Source
  │                                            │
  │ follows                              has_many
  ▼                                            ▼
User                                         Chunk
                                     (id, source_id, seq, offset_start,
                                      offset_end, locator, text,
                                      embedding_model_id,
                                      embedding_vector_ref)

Source ──── included_in ──────────────► CollectionItem
                                            │
Collection ◄─────────────────── belongs_to ─┘
  │
  ├── forked_from (nullable → Collection)
  ├── fork_lineage[] (ordered ancestor Collection IDs)
  └── included_in ───────────────────► KnowledgeBase_Collection

KnowledgeBase
  ├── vector_namespace (isolation boundary)
  ├── embedding_model_id
  ├── has_many → LearningPath
  └── has_one → VectorNamespace

LearningPath → Module → Assessment

Citation (id, module_id, chunk_id, quote_text, locator)
  — the guarantee that every output is anchored; addressable and persisted

DiscussionThread (id, anchor_type [collection|chunk|module], anchor_id, ...)
  — community permeates all layers via this polymorphic anchor

Enrollment (user_id, learning_path_id, progress_json, started_at)
CollectionACL (collection_id, principal_type, principal_id, permission)
APIKey (id, user_id, org_id, key_hash, scopes[], last_used_at)
```

### Source

```
Source {
  id:               UUID (PK)
  type:             enum [web_page, pdf, video, audio, image, plain_text,
                          code_file, epub]
  raw_url:          text (nullable)
  storage_key:      text (nullable — object storage path for uploads)
  title:            text
  owner_user_id:    UUID
  owner_org_id:     UUID (nullable)
  visibility:       enum [private, team, public]
  ingestion_status: enum [pending, processing, chunked, embedded, failed, stale]
  ingestion_job_id: UUID
  created_at:       timestamp
  metadata:         jsonb  -- authors, pub_date, language, page_count, duration_sec
}
```

Visibility is denormalized onto Source so the Retrieval Service can apply a namespace filter without joining to ACL tables on every query.

### Chunk

```
Chunk {
  id:                    UUID (PK)
  source_id:             UUID
  seq:                   integer        -- position in source
  offset_start:          integer
  offset_end:            integer
  locator:               text           -- page:3 | timestamp:01:23:45 | para:7
  text:                  text           -- normalized UTF-8 content
  media_type:            enum [text, image_region, transcript_segment]
  embedding_model_id:    UUID
  embedding_vector_ref:  text           -- pointer into vector store (namespace/id)
  created_at:            timestamp
}
```

Chunks are first-class addressable entities because Citations point to them and DiscussionThreads can anchor to them. The `locator` field is a human-readable, media-type-specific reference used for display.

### Collection

```
Collection {
  id:             UUID (PK)
  title:          text
  owner_user_id:  UUID
  owner_org_id:   UUID (nullable)
  visibility:     enum [private, team, public]
  forked_from_id: UUID (nullable — FK → Collection)
  fork_lineage:   UUID[]        -- ordered ancestor chain, root first
  layout_config:  jsonb         -- swim-lane vs canvas, layout state
  created_at:     timestamp
}

CollectionItem {
  id:            UUID (PK)
  collection_id: UUID
  source_id:     UUID
  added_by:      UUID
  note:          text           -- curator's annotation
  position:      integer
  added_at:      timestamp
}
```

A Board is a Collection with richer `layout_config`. No separate Board table — it's a property of Collection.

### KnowledgeBase

```
KnowledgeBase {
  id:                 UUID (PK)
  title:              text
  owner_user_id:      UUID
  owner_org_id:       UUID (nullable)
  vector_namespace:   text     -- namespace in the vector store; query-layer isolation
  embedding_model_id: UUID
  index_status:       enum [building, ready, stale, rebuilding]
  created_at:         timestamp
}
```

### LearningPath and Citation

```
LearningPath {
  id:                UUID (PK)
  kb_id:             UUID
  title:             text
  generation_status: enum [pending, generating, ready, outdated]
  visibility:        enum [private, team, public]
}

Module {
  id:               UUID (PK)
  learning_path_id: UUID
  title:            text
  summary:          text
  seq:              integer
  type:             enum [lesson, exercise, assessment, recap]
  body_json:        jsonb
}

Citation {
  id:         UUID (PK)
  module_id:  UUID
  chunk_id:   UUID
  quote_text: text
  locator:    text    -- mirrors Chunk.locator for display
}
```

---

## 3. Media Pipeline

### Upload and Processing Lifecycle

```
Phase 1 — SUBMIT
  Client → Ingestion API → IngestionJob created (status=pending)
         → Message published to ingestion.jobs queue
         → Job ID returned to client immediately

Phase 2 — FETCH/STORE
  Worker picks up job
  If raw_url: fetch content (robots.txt compliance, timeout)
  If upload: confirm object exists in object storage
  Store raw artifact: raw/{owner_user_id}/{source_id}/{filename_or_hash}
  Source.ingestion_status → processing

Phase 3 — PARSE + CHUNK
  Type-specific parser → normalized text + locator metadata:
    PDF       → pdfium/pypdf, page boundaries → locator "page:N"
    Video     → transcription job (async), timestamps → "ts:HH:MM:SS"
    Web page  → readability extraction, paragraph segmentation
    Code file → AST-aware chunker (function/class boundaries)
    Image     → vision model caption + OCR
  Chunks written to DB (status=chunked)

Phase 4 — EMBED
  Batch Chunk.text to embedding model API (batch size 256)
  Write vectors to vector store under the KnowledgeBase namespace(s)
  Store embedding_vector_ref and embedding_model_id on each Chunk
  Source.ingestion_status → embedded
  Event published: source.embedded {source_id, kb_ids[]}
```

### Async Job Queue Architecture

Three priority lanes:
- `ingestion.high` — browser extension clips, single-URL adds; target < 30s for typical web page
- `ingestion.standard` — PDF and single video uploads; target < 5 min for 50-page PDF
- `ingestion.batch` — bulk imports, re-embedding jobs; no SLA

Video/audio transcription handled by a separate `transcription.jobs` queue because duration-proportional processing time is the long pole. The IngestionJob tracks a `transcription_external_id` for async callback.

**Job deduplication:** keyed on `(owner_user_id, content_hash)`. Duplicate submission returns the existing Source ID without re-processing.

### Static Asset Serving

Raw media and derived assets are served from MinIO via the Nginx reverse proxy that sits in front of all services. Nginx handles:
- Short-lived signed URL generation (using Nginx's `secure_link` module) so media URLs are not guessable
- TLS termination for the entire platform (a single Let's Encrypt certificate covers all routes)
- Static asset caching in memory for thumbnails and frequently accessed derived assets

There is no external CDN. For a self-hosted platform with a community of hundreds to a few thousand users, Nginx with appropriate `Cache-Control` headers on static assets is sufficient. A CDN layer can be added later (e.g., Cloudflare's free tier) if geographic latency becomes an issue.

### Storage Management

```
All media:   MinIO on local disk (or bind-mounted local filesystem for single-user)
             One bucket: knomms-media
             Structure: {user_id}/{source_id}/{filename_or_hash}
             Nginx serves via signed URL; MinIO access is internal-only

Chunks:      PostgreSQL table (not object storage)
             Text is in the DB; vector refs point to pgvector columns in same DB

Retention:   No automatic tiering. Disk is cheap and self-managed.
             Operator prunes storage manually or via a cron job if needed.
             A Source deletion job tombstones chunks and queues MinIO object deletion.
```

---

## 4. Authentication and Authorization

### Auth Model

OAuth2 with PKCE for browser flows; client-credentials for service-to-service. Signed JWTs issued by Identity Service:

```json
{
  "sub":        "user:uuid",
  "org_id":     "org:uuid or null",
  "team_ids":   ["team:uuid"],
  "plan":       "free | pro | team | enterprise",
  "namespaces": ["ns:uuid", ...],
  "exp":        1234567890
}
```

The `namespaces` claim is the enforcement primitive. It contains all `vector_namespace` values the principal is permitted to query — computed at token issuance by joining the user's private KBs, team-shared KBs (via ACL), and public KB enrollments.

Access tokens: 15-minute expiry. Refresh tokens: server-side in Redis, 30-day TTL, revocable. On logout: refresh token deleted, access token added to short-lived blocklist.

### Multi-Tenant Isolation at the Query Layer

The isolation contract is enforced server-side, not UI-side:

1. Client sends a query with a JWT
2. API gateway validates JWT, extracts `namespaces` claim
3. Gateway injects resolved namespaces as a trusted internal header: `X-Resolved-Namespaces: ns:abc,ns:def`
4. Retrieval Service reads this header and **always** appends a namespace filter to every vector query: `filter: { namespace IN [ns:abc, ns:def] }`
5. The Retrieval Service **never** accepts a namespace from the request body or query string sent by the client — only from the trusted internal header
6. A middleware assertion in the Retrieval Service hard-fails if `X-Resolved-Namespaces` is absent

For full-text search, the same pattern: every query is wrapped in `WHERE source_id IN (SELECT id FROM sources WHERE vector_namespace IN (...))`, injected by a shared query builder library that cannot be accidentally omitted by individual handlers.

### Sharing and Permission Model

```
CollectionACL:
  viewer:  browse items, run Q&A against the collection's KB
  editor:  add/remove items, modify collection metadata
  owner:   delete, change visibility, manage ACL entries

Visibility:
  private:      owner only
  team:         all org members
  public:       unauthenticated can browse metadata;
                authenticated can fork and query
```

When a collection is forked, the new collection is owned by the forking user, starts `private`, and carries a `forked_from_id`. The original ACL is not copied.

### API Key Model

Each API key:
- Stored as a PBKDF2 hash; plaintext shown only at creation
- Carries a `scopes` list (e.g., `sources:read, sources:write, kb:query`)
- Has an optional `allowed_kb_ids` restriction
- Has a configurable rate limit
- Validated via Redis-backed cache (TTL 60s) — key revocation propagates within 60 seconds

---

## 5. Real-Time and Collaboration

### Live Presence in a Shared Board

WebSocket channel per Board, multiplexed through the Web BFF. Presence state lives in Redis (`board:{id}:presence:{user_id}` key with 30s TTL, refreshed by heartbeat every 10s). Expiry triggers a `user.left` event via pub/sub. Presence is never persisted to the relational database.

### Real-Time Ingestion Progress

Client subscribes to `source:{source_id}:progress` via WebSocket. Ingestion Service publishes to Redis pub/sub:

```json
{ "source_id": "...", "status": "processing", "phase": "chunking",
  "progress_pct": 45, "eta_sec": 12 }
```

For video transcription (10+ minutes for long content), progress reported at transcription completion stages (25%, 50%, 75%, 100%).

### Notification System

Notification Service subscribes to platform events:

```
source.embedded       collection.forked     learning_path.enrolled
kb.index_ready        user.followed         cohort.discussion_reply
```

Fan-out routing: in-app feed (write to `notifications` table), email (templated, queued), push (mobile device tokens, batched), webhook (if registered).

Fan-out bound: for followers in the thousands, fan-out is synchronous. Above a configurable threshold (default 10K followers), switches to lazy pull: followers see the event when they next open the platform. Tune this threshold below the saturation point; instrument from day one.

### Conflict Resolution for Concurrent Edits

**KnowledgeBase edits** (low-frequency): optimistic concurrency with a `version` integer. Mutating requests require `If-Match: version:N`. Conflicting writes return 409; client re-fetches and re-applies.

**Board item operations** (high-frequency, collaborative): log-structured positions. Item positions are stored as operations in an append-only `board_ops` log. Current state is derived by replaying the log. Conflicts resolved by last-write-wins per item with Lamport timestamp causal ordering. Two users can simultaneously reorder different items without conflict. Log compacted daily to a snapshot.

---

## 6. Search and Retrieval Infrastructure

### Unified Search Architecture

```
POST /v1/search
{
  "q": "transformer attention mechanism in NLP",
  "kb_ids": ["..."],
  "modes": ["semantic", "fulltext", "metadata", "graph"],
  "filters": { "source_type": ["pdf", "video"], "date_after": "2023-01-01" },
  "limit": 20
}
```

Four parallel retrieval modes:

**Semantic (vector):** ANN query against the vector store in resolved namespaces. Query text embedded in real-time using the same model version that produced the stored embeddings for those namespaces.

**Full-text (keyword):** PostgreSQL `tsvector` index over `chunks.text` with `ts_rank`. Scoped to `source_id IN (sources owned by permitted namespaces)` — the same predicate injection as the auth model.

**Metadata/filter:** Structured queries against Source metadata fields. Returns Sources rather than Chunks.

**Graph traversal:** Starting from a Chunk or Source, follow Citation edges (which Modules cite this Chunk?) and CollectionItem edges (which Collections contain this Source?). Two specific hops of a typed graph, handled with targeted SQL joins — not a general-purpose graph database.

### Index Architecture and Partition Strategy

Vector store namespaces map 1:1 to KnowledgeBases:

```
Namespace naming: kb:{kb_id}
  Private KB:  kb:a3f9...  — only in owner's JWT namespaces
  Team KB:     kb:c7b1...  — in all team members' JWTs
  Public KB:   kb:e2d4...  — in all authenticated users' JWTs
```

The vector store cluster is sharded by namespace prefix. Each shard owns a range of namespaces, allowing horizontal scaling without cross-shard queries for single-KB retrieval.

Full-text: `GIN` index on `tsvector` in PostgreSQL, partitioned by `source_id UUID prefix`.

### Query Latency Targets and Caching

```
Semantic search:       p50 < 100ms, p95 < 300ms
Full-text search:      p50 < 80ms,  p95 < 200ms
Merged search result:  p50 < 150ms, p95 < 400ms
Q&A (retrieval only):  p50 < 200ms, p95 < 500ms
Q&A (with generation): p50 < 2s,    p95 < 5s  (streaming)
```

Caching layers:
1. **Query result cache (Redis, TTL 60s):** keyed on `(query_embedding_hash, namespace_ids_hash, filters_hash)`. Cache-busted on `source.embedded` events.
2. **Embedding cache (Redis, TTL 24h):** keyed on `(model_id, text_hash)`. Avoids re-embedding identical query strings.
3. **Metadata filter cache (Redis, TTL 5min):** pre-materialized filter facets per namespace.

### Three-Layer Result Blending

```
SearchResult {
  item_type: enum [chunk, source, module, collection]
  item_id:   UUID
  layer:     enum [core, learning, discovery]
  score:     float (normalized 0–1)
  snippet:   text
  provenance: { source_id, locator }  -- always present
}
```

Blending uses Reciprocal Rank Fusion (RRF) across all four retrieval modes. RRF chosen over learned reranking for the MVP: requires no training data, is predictably fair across modes. A/B testing infrastructure is built in from day one for the eventual swap to a cross-encoder reranker.

Layer weighting: Core layer results rank above Learning layer for factual queries. Learning layer is boosted for "how do I learn X" / "explain Y" phrasing. Discovery layer (Collection results) appears at the bottom of the first page as a recommendation signal.

---

## 7. AI Infrastructure and Model Operations

### Local LLM Inference via Ollama

All LLM inference runs on-host via Ollama. See `docs/02-ai-architecture.md` §3.5 for model selection and hardware tiers. Platform-level concerns:

**Resource limiting:** Ollama runs as a system service (or Docker container) on the host. CPU/GPU resource limits are set at the container level in Docker Compose. The Generation Service enforces a request queue via Redis: concurrent generation requests are capped at `MAX_CONCURRENT_GENERATIONS` (default: 2 on GPU, 1 on CPU-only). Requests beyond the cap are queued and served as capacity frees. Users see a "queued" state indicator rather than a timeout.

**Request tracking (no monetary cost, but resource-aware):**

```
AICall {
  id:               UUID
  user_id:          UUID
  feature:          enum [qa, curriculum_generation, summary, embedding,
                         assessment_generation, intent_classification]
  model:            text       -- which Ollama model was used
  prompt_tokens:    integer
  completion_tokens: integer
  latency_ms:       integer
  queue_wait_ms:    integer    -- time spent waiting for a generation slot
  created_at:       timestamp
}
```

This table serves resource monitoring (which features are compute-heavy, which users generate the most load) rather than cost billing. No `estimated_cost_usd` field — there is no per-token cost.

**Retry policy:** Ollama errors fall into two categories: load errors (model not yet warm — retry after 5s, up to 3 times) and generation errors (malformed output — surface to user, do not retry automatically).

### Model Versioning

Model version is a first-class attribute, not a configuration value:

```
EmbeddingModelVersion {
  id:            UUID (PK)
  provider:      text
  model_name:    text
  dimension:     integer
  deprecated_at: timestamp (nullable)
  successor_id:  UUID (nullable — FK → EmbeddingModelVersion)
}
```

Migration strategy for embedding model upgrades:
1. Register the new model as an `EmbeddingModelVersion`
2. New KnowledgeBases default to the new model
3. **Existing KBs continue to function with the old model indefinitely** — their queries embed with the old model at query time (Retrieval Service reads `kb.embedding_model_id`)
4. A background `ReembeddingJob` re-embeds all Chunks with the new model, writing vectors to a new namespace
5. When the job completes, the KB's `embedding_model_id` and namespace flip atomically
6. The old namespace remains live until the atomic flip — zero downtime

### Batch vs Real-Time Inference

```
Real-time (user-facing latency SLA):
  Query embedding, Q&A generation (streaming), search reranking,
  source summary on view

Background (no latency SLA):
  Chunk embedding during ingestion, curriculum generation,
  assessment generation, re-embedding on model migration,
  expertise tag inference, recommendation pre-computation
```

Background jobs use a separate worker pool provisioned for throughput rather than latency.

Curriculum generation is broken into stages: outline generation → per-module content generation → assessment generation. Each stage is a separate queue message, allowing partial work to survive worker restarts and enabling UI progress reporting.

### Observability

**Tracing:** Every AI call participates in a distributed trace including retrieval context (Chunks fetched, scores), rendered prompt, and completion. Trace ID stored on `AICall` record.

**Prompt/completion logging:**
- Full prompts and completions are logged
- Chunk text from user sources stored in the trace store with a shorter retention policy (7 days vs. 90 days for general application logs)
- Traces tagged with `sensitivity: private` for private KB content
- Per-organization logging opt-out for enterprise tier (contractual data residency requirements)

**Cost dashboards:** Aggregated from `DailyCostRollup`. Exposed to users as "AI usage" in account settings, broken down by feature. Per-tenant cost attribution for operators.

---

## 8. Developer Platform and Extensibility

### Public API Surface

All responses include a `citations` array where relevant:

```json
{
  "answer": "Transformer attention computes...",
  "citations": [
    { "chunk_id": "...", "source_id": "...", "locator": "page:14",
      "quote": "The attention function maps a query..." }
  ]
}
```

The citation array is never empty for generation responses. A generation that produces no citations returns an error code `ungrounded_response`, giving developers the choice of how to surface this to their users.

Core endpoints:

```
Sources:
  POST   /v1/sources                  # submit for ingestion
  GET    /v1/sources/{id}             # metadata + status
  GET    /v1/sources/{id}/chunks      # list chunks with locators

Collections:
  GET/POST/PUT /v1/collections
  POST   /v1/collections/{id}/items
  DELETE /v1/collections/{id}/items/{source_id}

KnowledgeBases:
  POST   /v1/kbs/{id}/query           # Q&A with citations
  GET    /v1/kbs/{id}/search          # retrieval without generation

Learning:
  GET    /v1/learning-paths/{id}
  GET    /v1/learning-paths/{id}/modules
```

### Webhook Events

Webhooks registered per-API-key with HTTPS endpoint and event subscriptions. Delivery: exponential backoff (1s, 2s, 4s, 8s, max 5 retries). Endpoint suspended after 10 consecutive delivery failures.

Event schema:

```json
{
  "event_id":    "evt:uuid",
  "event_type":  "source.embedded",
  "created_at":  "ISO8601",
  "api_version": "2025-01",
  "data":        { ... event-specific payload ... }
}
```

Payloads signed with HMAC-SHA256 using a secret shared at registration time.

Published events: `source.submitted`, `source.embedded`, `source.failed`, `collection.forked`, `kb.index_ready`, `learning_path.generated`

### Plugin and Extension Model

**Custom ingestion adapters:** Third-party developers register a custom source type by implementing an HTTPS adapter endpoint. The adapter contract:

```
POST https://your-adapter.example.com/fetch
Input:  { url, options }
Output: { title, text, chunks?: [{ text, locator }], metadata }
```

The Ingestion Service calls the registered adapter URL when a source URL matches the registered pattern. Adapters run in the developer's infrastructure; the platform does not execute third-party code. The platform only handles subsequent embedding and indexing.

**Custom agent tools:** Developers register tools (with OpenAPI-compatible schemas) that the Generation Service can call during agentic workflows. Tool calls are logged in the `AICall` trace and count against the API key's rate limit. The tool interface mirrors standard tool-use formats, so developers familiar with other platforms find the interface familiar.

---

## 9. Scalability and Resource Model

### Cost Structure

The platform has **zero software licensing cost** for any component. All services are open-source and self-hosted. The only costs are:

- **Hardware / hosting**: a machine to run it on. Options:
  - Repurposed or owned server: €0/month ongoing (one-time hardware cost)
  - Hetzner dedicated server (AX41, 64GB RAM, 2× 512GB NVMe): ~€50/month — viable for a community of hundreds to a few thousand users
  - A cloud VM with a GPU (e.g., Vast.ai RTX 3090 spot): ~$0.30–$0.60/hour, ~$100–$200/month if running continuously
- **Electricity**: ~50–250W average draw depending on inference load; ~$5–20/month at typical residential rates
- **Domain name**: ~$10–20/year, optional

There is no per-query cost, no per-token cost, no per-user cost. Adding a 1,000th user costs no more in software terms than the 10th.

### Disk and Memory Sizing

Sizing for a self-hosted community deployment (hundreds of users):

```
Per-user storage estimate:
  Raw media (200 sources × 5MB avg):            ~1GB/user
  Chunk text in PostgreSQL (12,500 chunks):      ~6MB/user
  pgvector index (768-dim × 12,500 vectors):     ~37MB/user (float32)
                                    or           ~19MB/user (float16 compressed)
  MinIO object storage totals:                   ~1GB/user
  
For 100 active users:
  Disk:   ~100GB total (affordable on any modern host)
  RAM:    pgvector HNSW index lives in RAM for fast ANN: ~3.7GB for 100 users
          + PostgreSQL buffer pool: 4–8GB
          + Redis: <500MB
          + Ollama model in VRAM: 10–40GB depending on model
  Total host RAM recommendation: 32–64GB
```

### Scaling Inflection Points

**pgvector HNSW RAM ceiling:** At ~37MB per user, 1,000 users = ~37GB of vector data. This fits comfortably in RAM on a 64GB host. At 10,000 users, the index (~370GB) exceeds RAM — at that scale, migrate to pgvector's IVFFlat index (disk-backed, lower recall but manageable) or to self-hosted Qdrant. This is a generous runway — most self-hosted communities will not exceed 1,000 active users.

**Inference throughput:** A single GPU handles 2–5 concurrent generation requests before queuing. This is adequate for a community of hundreds; for thousands of concurrent users, either add a second GPU node or accept queue latency. Embedding (ingestion-time) is batch-processed in the background and does not compete with interactive Q&A for GPU capacity if scheduled during low-traffic hours.

**Notification fan-out:** For a small self-hosted community, synchronous fan-out is fine up to a few thousand followers. The lazy-pull threshold (default 10K) will not be hit at typical self-hosted scales.

**Embedding model migration:** Re-embedding 1,000 users × 12,500 chunks = 12.5M chunks. At 8,000 chunks/min on a GPU, this takes ~26 hours — acceptable as an overnight background job. On CPU-only at 800 chunks/min, this takes ~10 days; plan accordingly or run the migration across multiple nights.

### No "Free Tier" Needed

Free tiers exist to manage per-query costs in a commercial SaaS. On a self-hosted deployment, there is no such cost to manage. The operator determines user limits based purely on disk and compute headroom — not on per-user billing math. A typical configuration:

```
All users:
  Sources:          unlimited (bounded only by disk)
  Q&A queries:      rate-limited for fairness (e.g., 10 concurrent, not 10/month)
  LearningPaths:    unlimited
  Storage:          per-user disk quota configurable by operator (default: none)
```

The platform ships with configurable resource quotas so operators can prevent a single user from ingesting 10TB of video, but quotas are fairness controls — not monetization levers.
