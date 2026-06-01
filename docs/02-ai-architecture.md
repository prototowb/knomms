# Knowledge Commons — Layer 1: Grounded Knowledge Core

## AI Architecture Specification

**Version:** 1.0 — Grounded Knowledge Core
**Layer:** 1 of 3
**Audience:** Engineering leads, ML engineers, backend architects

---

## Table of Contents

1. [Multimodal Ingestion Pipeline](#1-multimodal-ingestion-pipeline)
2. [Embedding and Vector Storage](#2-embedding-and-vector-storage)
3. [Retrieval-Augmented Generation Architecture](#3-retrieval-augmented-generation-architecture)
4. [Agentic Workflow Layer](#4-agentic-workflow-layer)
5. [Guardrails and Evaluation](#5-guardrails-and-evaluation)
6. [Knowledge Graph Layer](#6-knowledge-graph-layer)
7. [Privacy and Data Architecture](#7-privacy-and-data-architecture)
8. [MVP vs Full Build](#8-mvp-vs-full-build)

---

## 1. Multimodal Ingestion Pipeline

### 1.1 Design Principle

The ingestion pipeline is not a pre-processing step that feeds a separate content system. It is the act of constructing the semantic substrate. Every source that enters the platform is transformed into a graph of addressable, citable passage units. The pipeline must preserve provenance at every transformation step so that the final semantic chunk retains enough metadata to be quoted, attributed, and linked back to its origin.

### 1.2 Supported Source Types and Normalization

Each source type has a dedicated extractor that outputs a common intermediate representation (CIR): a sequence of `RawBlock` objects. A `RawBlock` carries:

- `text: str` — normalized UTF-8 text content
- `source_id: uuid` — stable identifier for the parent source document
- `block_index: int` — monotonically increasing integer within the document
- `page_or_position: str` — human-readable locator (e.g., "p. 14", "00:03:45", "row 1240")
- `block_type: enum` — `BODY`, `HEADING`, `CAPTION`, `TRANSCRIPT`, `TABLE_ROW`, `ALT_TEXT`
- `raw_offset: int` — byte offset in original file (where applicable)
- `language: str` — ISO 639-1 language code, detected at extraction

This CIR is the contract between extractors and the downstream chunker. Extractors are responsible for all format-specific logic; the chunker and embedder see only CIRs.

**PDF**
Use `pdfminer.six` for text-layer PDFs with structural heuristics (bounding-box column detection, heading classification by font size). For scanned PDFs, fall through to OCR. Preserve page numbers in `page_or_position`. Tables are extracted as structured rows; each row becomes a separate `TABLE_ROW` block with a header context prefix injected at embedding time.

**DOCX**
Use `python-docx`. Paragraphs map directly to `RawBlock`s. Style names (Heading 1–4, Normal, Caption) determine `block_type`. Comments and tracked changes are stripped unless the operator flag `ingest_annotations=True` is set.

**Web URLs (crawl/scrape)**
Fetch HTML with a headless browser worker (Playwright) to handle JavaScript-rendered content. Strip navigation, footers, ads, and boilerplate using a readability heuristic (a port of Mozilla's Readability algorithm). The clean article body is then split by `<p>`, `<li>`, and heading tags into `RawBlock`s. `page_or_position` is set to a stable fragment URL where possible (using `id` attributes). Crawl depth is capped at 1 for linked resources unless the user explicitly enables multi-page site ingestion. Crawl rate is throttled to 1 req/s with `robots.txt` compliance enforced.

**YouTube and Video (transcript extraction)**
For YouTube URLs, prefer the closed-caption/subtitle track via the `youtube-transcript-api` library, which returns timestamped segments. For uploaded video files, run Whisper (the `large-v2` variant in self-hosted mode, or the managed transcription API in cloud mode) to produce a word-level transcript. Transcript segments are merged into sentence-level `RawBlock`s using punctuation detection, with `page_or_position` set to the start timestamp (`HH:MM:SS`). This timestamp becomes the deep-link anchor for in-platform citations.

**Images (OCR + visual description)**
Two passes. First, Tesseract 5 handles OCR for images that are primarily text (e.g., scanned slides, screenshots of documents). Second, a multimodal vision model produces a brief semantic description of the visual content (layout, diagram type, subject matter) for images where text is sparse. Both outputs become separate `RawBlock`s with `block_type=ALT_TEXT`. The visual description is explicitly marked as AI-generated to distinguish it from extracted text in attribution chains.

**Audio**
Same pipeline as video transcript extraction — Whisper produces timestamped segments — but without a video frame analysis pass. Speaker diarization (via `pyannote.audio`) is applied where multiple speakers are detected; speaker labels are preserved as metadata and injected as prefixes into `RawBlock` text (`[Speaker A]: ...`).

**Structured Data (CSV, JSON)**
CSVs: headers become context; each row becomes a `TABLE_ROW` block with a synthetic sentence prefix (`"Row {n} of {source_name}: column1=val1, column2=val2, ..."`). This verbalization is necessary because embeddings are trained on natural language. The original structured data is stored separately and the verbalized form is used only for embedding. JSON: if the schema is flat or one level deep, treat as CSV equivalent. Deeply nested JSON requires the user to supply a JSONPath template that specifies which fields to verbalize; otherwise ingestion is rejected with a schema complexity warning.

### 1.3 Chunking Strategy

**Rationale for semantic chunking over fixed-window:** Fixed-window chunking (e.g., 512 tokens with 64-token overlap) is operationally simple but semantically incoherent — a chunk boundary may split a sentence mid-thought, and two chunks may carry identical content in their overlap without the retriever knowing they belong to the same passage. Semantic chunking respects natural discourse boundaries and produces chunks that are independently meaningful for citation.

**Algorithm:**

1. Group consecutive `RawBlock`s of type `BODY` and `CAPTION` into candidate segments at heading boundaries. A new heading block always starts a new segment.
2. Within a segment, apply a sliding sentence window. Measure the semantic similarity between adjacent sentences using a lightweight bi-encoder (a small cached model, not the main embedding model). When similarity drops below threshold τ = 0.65, a boundary is inserted.
3. Merge very short segments (< 80 tokens) with their successor. Split very long segments (> 600 tokens) at the sentence boundary nearest the midpoint.
4. Target chunk size: 300–500 tokens (body text). Table rows and transcript segments are chunked independently at 200 tokens, since they carry dense factual content at lower density.

**Overlap:** A 20% token overlap is applied between adjacent body chunks within the same heading section — approximately 60–100 tokens. The overlap carries a `is_overlap=True` flag so the retriever can de-duplicate at result merge time. Overlap is not applied across heading boundaries; heading context is instead injected as a prefix into the first chunk of each new section.

**Metadata preserved on each chunk:**
- `source_id`, `collection_id`, `user_id` (owner)
- `chunk_index`, `block_index_start`, `block_index_end`
- `page_or_position_start`, `page_or_position_end`
- `heading_path` — e.g., `["Chapter 3", "3.2 Methodology", "Data Collection"]`
- `block_types` — set of block types contributing to this chunk
- `char_count`, `token_count`
- `language`
- `ingest_timestamp`, `source_last_modified`

This metadata is stored in the vector DB payload and in a relational table (`chunks`) so it remains queryable without a vector operation.

### 1.4 De-duplication Across Re-ingestion

Re-ingestion is common (a user updates a PDF, re-pastes a URL). Naive re-ingestion would produce duplicate embeddings that confuse retrieval by inflating certain passages' apparent relevance.

**Content fingerprinting:** At the `RawBlock` level, compute a SHA-256 hash of the normalized block text (after whitespace normalization, Unicode NFKC normalization, and lowercasing). Store this hash in the `chunks` table with a `(source_id, block_hash)` unique index.

**On re-ingestion:** For each incoming block, check against the hash table. If a matching hash exists under the same `source_id`, skip re-embedding. If the `source_id` is new but the hash matches a block from a different source (cross-document duplicate), flag it in the `duplicate_refs` table — this is valuable signal for the Knowledge Graph layer, which may want to represent convergent evidence.

**Tombstoning:** When a source is deleted, its chunks are tombstoned rather than immediately removed, to allow in-progress queries referencing those chunks to resolve gracefully. A background sweep removes tombstoned records after a configurable TTL (default 24 hours).

---

## 2. Embedding and Vector Storage

### 2.1 Embedding Model Selection

Three candidates warrant serious evaluation. The choice is not obvious and depends heavily on which constraints dominate.

**`nomic-embed-text-v1.5` (open-source, self-hosted)**
Dimensionality: 64–768 via MRL, with 8192-token context window — the longest context window of any embedding model in this tier, meaningful for ingesting long transcript segments or dense technical paragraphs without forced mid-chunk truncation. Apache 2.0 licensed, self-hostable on commodity GPU (fits comfortably on a single A10G/24GB). Batch throughput on such hardware: approximately 5,000–8,000 chunks/minute at 768 dimensions. Quality is competitive with larger proprietary models on domain-general retrieval; it shows slightly weaker performance on highly specialized scientific text. No data egress; all embedding computation stays within the platform's trust boundary.

**CLIP-family (multimodal)**
CLIP and its derivatives (e.g., `openclip`, `SigLIP`) embed images and text into a shared vector space, enabling cross-modal retrieval (find the image most relevant to a text query). This is powerful but introduces architectural complexity: the text embedding space of a CLIP model is not interchangeable with a language-specialized embedding space, requiring either a unified multi-space retrieval layer or a separate image-only index.

**Decision: `nomic-embed-text-v1.5` is the primary embedding model, self-hosted via Ollama.**

The rationale: The platform's hard constraint is zero external service cost and full data sovereignty. `nomic-embed-text-v1.5` is Apache 2.0 licensed, runs locally via Ollama with no API key or network egress, and achieves competitive retrieval quality on the MTEB benchmark. The 8192-token context window reduces forced chunk splits for long-form content. The MRL dimensionality dial (256 for fast ANN, 768 for high-precision re-ranking) maps cleanly onto the hybrid retrieval architecture in §2.3. An alternative embedding model can be configured via the swappable `EmbeddingAdapter` interface (see §7 of `docs/05-platform-architecture.md`), but the default path sends no data outside the host machine.

CLIP is deferred to the full build. In the MVP, image content is represented by its OCR text and AI-generated description, which are embedded in the same text space as all other chunks. This is semantically lossy for purely visual content but avoids a separate index path.

### 2.2 Operational Parameters

| Parameter | Value | Rationale |
|---|---|---|
| Embedding dimensions (default) | 768 | Maximum quality; compressible to 256 for ANN index |
| ANN index dimensions | 256 | 3× storage reduction; acceptable recall loss for first-pass retrieval |
| Re-ranking dimensions | 768 | Full precision for cross-encoder input |
| Max chunk tokens | 600 | Safely within 8192-token context |
| Batch size (GPU) | 128 | Saturates A10G memory without OOM |
| Ingest throughput target | 10,000 chunks/min (horizontal) | Drives GPU worker scaling |
| Embedding cache TTL | 7 days | Re-ingestion of unchanged blocks hits cache |

Embedding cost: zero in software licensing terms. The only cost is electricity and amortized hardware. Embedding throughput depends on the host GPU: a single NVIDIA RTX 3090 (24GB) achieves ~8,000 chunks/minute at 768 dimensions with `nomic-embed-text-v1.5`; on CPU only (e.g., a VPS without GPU), throughput drops to ~800 chunks/minute, which is acceptable for background ingestion jobs but not for real-time embedding. GPU is strongly recommended for production; CPU-only is viable for small self-hosted deployments with patient ingestion queues.

### 2.3 Vector Database Selection

Four candidates:

**pgvector** — A PostgreSQL extension adding vector column types and approximate nearest-neighbor (ANN) indexes (IVFFlat, HNSW). The decisive advantage is operational simplicity: if the platform already runs on PostgreSQL (which it should for relational metadata — the `chunks`, `sources`, `collections`, `users` tables all belong in a relational store), pgvector adds vector search to the same database instance. No separate service, no data synchronization, no dual-write logic. Row-level security (RLS) enforced at the database layer provides per-user and per-collection isolation without application-level guards. HNSW indexing gives sub-millisecond query latency at millions of vectors with recall >0.95. Trade-offs: performance degrades significantly beyond ~50M vectors on a single node; horizontal sharding requires `Citus` or application-level partitioning; no built-in payload filtering as fast as a dedicated vector DB.

**Qdrant** — A purpose-built vector database with strong payload filtering, native multi-tenancy via collection namespaces, and HNSW with hardware-optimized SIMD kernels. Outperforms pgvector on raw ANN throughput at scale (>10M vectors). Offers a rich payload filter API that enables hybrid vector+attribute queries in a single call. Trade-offs: a second stateful service to operate, meaning separate backup, scaling, and failure domain management. No SQL; all queries via its own gRPC/REST API. The operational overhead is justified at scale but adds friction in the early platform.

**Weaviate** — Combines vector search with a built-in graph-like schema and native hybrid search (BM25 + vector). The schema system is powerful for structured collections but introduces an impedance mismatch with the platform's own data model — the platform owns the schema, not the vector DB. Weaviate's hybrid search implementation is convenient but not as tunable as building hybrid retrieval explicitly. Managed cloud option reduces operational burden but reintroduces data egress concerns.

**Pinecone** — Fully managed, serverless vector search. **Not an option.** Proprietary, no self-hosted path, all data transits external infrastructure. Excluded by the self-hosted constraint.

**Decision: pgvector for MVP and full build (unless a single deployment exceeds ~20M chunks, at which point Qdrant self-hosted is the defined migration path).**

The rationale: the platform's most acute early constraint is operational complexity, not vector throughput. A single PostgreSQL instance with pgvector handles tens of millions of chunks with HNSW indexing and provides RLS-enforced multi-tenancy out of the box. The `chunks` table and the vector index coexist in one database; joins between vector results and relational metadata require no inter-service calls. When the platform grows beyond ~20M chunks per deployment or requires sub-5ms P99 ANN latency under high concurrency, a migration to Qdrant is the defined path — and because the platform wraps vector DB access behind a `VectorStore` interface, the migration is an implementation swap, not an architectural change.

### 2.4 Hybrid Retrieval: Dense + Sparse Fusion

Neither pure dense retrieval nor pure sparse (keyword) retrieval is sufficient for a knowledge-intensive platform:

- Dense retrieval excels at semantic paraphrase matching ("what is the author's view on X" → chunk that discusses perspective Y without using the word "view"). It fails on exact-match lookups (specific names, codes, formulas, verbatim quotes).
- Sparse retrieval (BM25) excels at exact-match and rare-term queries. It fails when the user's phrasing differs from the source vocabulary.

**Implementation:**

1. **Dense pass:** ANN search using the query embedding, returning top-100 candidates with cosine similarity scores.
2. **Sparse pass:** BM25 search using `elasticsearch`-compatible inverted index (self-hosted, or using PostgreSQL's `tsvector`/`tsrank` for MVP), returning top-100 candidates with BM25 scores.
3. **Score fusion:** Reciprocal Rank Fusion (RRF) is used to merge the two ranked lists into a single ranked list of ~150 unique candidates. RRF is preferred over linear score combination because it is robust to score scale differences between dense and sparse systems — there is no hyperparameter to tune per query type.
4. **Cross-encoder re-ranking:** The top-150 RRF candidates are passed to a cross-encoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2` or equivalent) that scores each (query, chunk) pair jointly. The cross-encoder has access to the full 768-dimension semantic relationship between query and passage, unlike the bi-encoder retrieval models. It returns the top-20 chunks by cross-encoder score; these are what the RAG layer receives.

The two-stage (retrieval → re-ranking) design is intentional: the ANN and BM25 stages are fast (~10ms) and maximize recall; the cross-encoder stage is slower (~100–200ms for 150 pairs) but maximizes precision. The overall retrieval latency budget is 250ms.

---

## 3. Retrieval-Augmented Generation Architecture

### 3.1 Query Planning: Intent Classification

Before any retrieval occurs, an incoming query is classified into one of four intent types by a lightweight classification head (a fine-tuned small language model, 3B–7B parameter range, low latency):

| Intent | Description | Retrieval strategy |
|---|---|---|
| `LOOKUP` | Factual question with a specific, bounded answer | Single-hop retrieval; top-5 chunks; short generation |
| `SYNTHESIS` | Requires drawing threads across multiple sources or sections | Multi-hop retrieval; top-20 chunks; structured generation with section headers |
| `COMPARISON` | Asks how two sources, authors, or arguments relate to each other | Parallel retrieval against each pole of the comparison; contrastive generation |
| `GENERATION` | Requests a novel artifact grounded in the corpus (summary, outline, quiz) | Full context assembly; agent handoff (see §4) |

The classification output also includes:
- `scope: [SINGLE_SOURCE | COLLECTION | GLOBAL]` — whether the query is implicitly scoped to a specific source, a user-defined collection, or the full corpus
- `requires_recent: bool` — whether the query implies time-sensitivity (triggers a recency-boosted retrieval pass)
- `query_entities: list[str]` — named entities extracted for use in the knowledge graph traversal (§6)

Classification adds approximately 50ms to the query latency and is worth it: routing `LOOKUP` queries through the multi-hop pipeline wastes both latency and context window budget, while routing `SYNTHESIS` queries through a single-hop retrieval produces incomplete answers that erode user trust.

### 3.2 Multi-Hop Retrieval for Synthesis Queries

For `SYNTHESIS` queries, a single retrieval pass is insufficient — the answer depends on passages that are not all lexically or semantically close to the original query phrasing. Multi-hop retrieval follows a structured sequence:

1. **Initial retrieval:** Run hybrid retrieval (§2.4) against the original query. Collect top-10 chunks.
2. **Gap detection:** Pass the initial chunks and query to the LLM with a structured prompt: *"Given this query and these retrieved passages, identify what information is still missing. List specific sub-questions."* The LLM returns a list of 2–4 sub-questions.
3. **Sub-query retrieval:** Run hybrid retrieval for each sub-question. Collect top-5 chunks per sub-question.
4. **Deduplication:** Merge all retrieved chunks; de-duplicate by `chunk_id`; re-rank the merged set using the cross-encoder against the original query.
5. **Final assembly:** Take the top-20 chunks from the re-ranked merged set as the RAG context.

The hop count is capped at 2 (one round of sub-question generation). Deeper recursion is diminishing-returns territory and introduces compounding latency. For the rare query requiring 3+ hops, the system falls back to the agent layer (§4.1, Synthesis Agent) which has a longer planning horizon.

### 3.3 Citation Format

Citation is not a post-processing step — it is enforced by the prompt structure. The LLM is instructed to produce outputs in a structured citation format:

**Generation format:**

```
[claim or sentence] [SOURCE:chunk_id_1, chunk_id_2]
```

The `chunk_id` values in the generated text are resolved at render time by the platform's citation service, which fetches the corresponding chunk records from the database and expands them into:
- The verbatim passage text (±20 tokens of surrounding context for readability)
- The source document name and page/timestamp locator
- A stable deep link into the source document's viewer

The LLM never fabricates `chunk_id` values because the prompt injects the chunk IDs alongside the passage texts in a structured context block:

```
[PASSAGE chunk_id=abc123 source="Smith 2023, p.14" heading="Methodology"]
The data was collected over a 12-month period using ...
[/PASSAGE]
```

The LLM is instructed to cite only chunk IDs from passages that appear in the context block. A post-generation validation step (§5.1) checks every cited `chunk_id` against the context block's IDs and flags hallucinated citations.

**Citation granularity trade-off:** Sentence-level citation is preferred over paragraph-level because it gives users the highest precision — they can trace exactly which sentence supports a claim. However, sentence-level citation requires the LLM to be more deliberate and slightly inflates token count. The instruction set trains the model to cite at the sentence level for factual claims and at the paragraph level for summarizations.

### 3.4 Context Window Management

The cross-encoder returns top-20 chunks. At ~400 tokens per chunk, the raw context is ~8,000 tokens — manageable within a 128k-context LLM. However, context assembly must be deliberate to avoid two failure modes: (a) the most relevant passages buried in the middle of the context (the "lost in the middle" problem), and (b) excessive overlap content inflating perceived context diversity.

**Assembly rules:**

1. **De-overlap:** Remove chunks flagged `is_overlap=True` if their non-overlapping counterpart is already in the set.
2. **Sort by relevance descending, then group by source.** Interleaving passages from the same source next to each other reduces the LLM's context-switching cost during generation.
3. **Place highest-scored chunks at the start and end of the context block.** This directly addresses the "lost in the middle" problem — the LLM attends most reliably to the beginning and end of long contexts.
4. **Inject source metadata as context headers.** Each source group is prefaced with a brief metadata header: `[Source: {title}, {date}, {type}]`. This allows the LLM to attribute at the source level for narrative summaries even when citing at the chunk level.
5. **Token budget:** Reserve 2,000 tokens for the system prompt and instructions, 2,000 tokens for the generated response, and the remainder (up to the model's context limit, minimum 20,000 tokens) for retrieved context. If the retrieved context exceeds the token budget, truncate by dropping the lowest-scored chunks first.

For very long contexts (full-book ingestion, large collection synthesis), a map-reduce generation strategy is applied: the corpus is partitioned into batches, each batch is summarized with citations, and the summaries are synthesized in a final reduction pass. This trades single-pass coherence for coverage; it is flagged to the user with a "synthesized across batches" notice.

---

## 3.5 Local LLM Inference Runtime

All generation and classification inference runs locally via **Ollama**. Ollama provides:
- A unified REST API (`POST /api/generate`, `POST /api/chat`) across any supported model
- Hardware auto-detection: GPU acceleration on CUDA/ROCm/Metal; transparent fallback to CPU with quantized models
- Model library: Llama 3, Mistral, Qwen2, Phi-3, Gemma 2, and others, pulled on demand from the Ollama registry
- Concurrent request handling with a built-in queue
- No network egress — inference is entirely on-host

**Recommended generation models by deployment tier:**

| Tier | Model | VRAM / RAM | Use case |
|---|---|---|---|
| GPU (24GB) | `llama3:70b-instruct-q4_K_M` | ~40GB VRAM | Best quality; production recommended |
| GPU (8–12GB) | `mistral:7b-instruct-q8_0` or `llama3:8b-instruct` | ~8–10GB VRAM | Good quality; fast inference |
| CPU-only (16GB RAM) | `phi3:mini-instruct-q4_K_M` | ~2.5GB RAM | Acceptable quality; slow for synthesis tasks |

The Generation Service communicates with Ollama via its HTTP API over localhost. The service wraps Ollama with:
- Retry logic (model loading on first call can take 5–30s depending on model size)
- Streaming response forwarding to the client (Ollama supports token-level streaming)
- Timeout enforcement (120s hard timeout per generation request)
- A model warm-up ping on service start to pre-load the model into GPU memory

**Model selection is operator-configurable** via `OLLAMA_MODEL` in the deployment environment file. The platform enforces that whatever model is selected must be capable of instruction-following and JSON-structured output (validated at startup via a probe prompt).

**The intent classification model** (§3.1) runs on a separate smaller model via Ollama (`phi3:mini-instruct` or `llama3:8b-instruct`) to avoid loading the large generation model for every classification call. Classification adds ~50–150ms depending on hardware tier.

**The NLI faithfulness scorer** (§5.1) uses `cross-encoder/nli-deberta-v3-small` (via `sentence-transformers`, not Ollama) because NLI cross-encoders are 100M-parameter discriminative classifiers — much cheaper to run than a generative LLM for a binary entailment judgment.

---

## 4. Agentic Workflow Layer

### 4.1 Agent Types

The platform defines four agents, each with a distinct task profile, tool set, and output contract.

**Synthesis Agent**
Compiles thematic insights across a collection or the full corpus. Input: a synthesis prompt and a collection scope. Process: query planning (§3.1) identifies this as a `GENERATION` intent, multi-hop retrieval (§3.2) assembles the context, and the agent structures the output as a thematic report with inline citations. The agent can iteratively issue sub-queries during generation if it detects a coverage gap. Output: a structured document with H2-level theme headings, cited prose, and a provenance manifest listing every chunk referenced. This is the platform's primary value-creation agent — it is always available, not gated.

**Curriculum Agent**
Proposes a learning path through a collection. Input: a learning goal (free text) and a collection. Process: the agent first retrieves an overview of the collection's conceptual structure (using heading metadata and high-level chunk summaries), then sequences source materials into a progression of steps. It tags each step with a prerequisite concept and an estimated reading time. Output: a structured learning path with step titles, recommended source passages, and rationale for ordering. This agent does not generate explanatory content — it routes users to existing source passages rather than synthesizing new content, which is a deliberate design constraint to keep attribution intact.

**Assessment Agent**
Generates grounded quizzes from source material. Input: a set of chunks or a collection scope, a question format (multiple choice, short answer, concept matching), and a difficulty target. Process: the agent extracts key claims and definitions from the retrieved passages, constructs questions whose correct answers are directly traceable to specific passages, and generates plausible distractors (for multiple choice) derived from related-but-distinct passages within the corpus. Each question carries a `citation_chunk_ids` field pointing to the passage that supports the correct answer. This allows the platform to display the source passage as the explanation when a user answers incorrectly. The agent must not generate questions whose answers are not supported by an identifiable passage — this is enforced by the guardrails layer (§5).

**Debate Agent**
Steelmans two sources, authors, or positions against each other. Input: a debate framing (e.g., "Source A argues X while Source B argues Y — steelman both") and the relevant collection scope. Process: separate parallel retrieval passes are run against each pole of the debate. The agent is prompted to construct the strongest possible version of each position using only passages from that pole's retrieval set, then identify specific passages where the two positions address the same underlying question differently. Output: a structured debate brief with position A, position B, and a "points of genuine disagreement" section — all with inline citations. The agent is explicitly instructed not to adjudicate between positions; its role is exposition, not verdict.

### 4.2 Orchestration Framework

**Candidates evaluated:**

**LangGraph** — A graph-based orchestration framework built on LangChain that represents agent workflows as directed graphs with typed state. Each node is a callable (LLM call, tool call, conditional branch). State is immutable and transitions are explicit. Cycles (for iterative retrieval loops) are first-class. The framework's main strength is that workflow topology is inspectable and serializable — the state at any node can be checkpointed, which is essential for the human-in-the-loop requirements in §4.4. Its main weakness is that complex workflows accrete LangChain abstractions that become opaque over time.

**AutoGen** — A multi-agent conversation framework where agents communicate via message passing in a conversation loop. Suited for open-ended collaborative tasks. The conversation metaphor is expressive but harder to bound: agents can take arbitrarily many turns, which creates latency and cost unpredictability. Not well-suited for the platform's agents, which have bounded, structured outputs.

**Custom state machine** — Full control, no framework debt. The trade-off is implementing serialization, retries, parallelism, and tooling from scratch — high engineering cost for capabilities LangGraph provides.

**Decision: LangGraph.**

The rationale: the platform's agents have well-defined topologies (retrieval → gap detection → sub-retrieval → generation, for instance), not open-ended conversation loops. LangGraph's graph model maps cleanly onto these topologies. Checkpointing at node boundaries is built-in and maps directly to the human-in-the-loop pause points. The state serialization enables async agent execution (a long synthesis job can be paused, persisted, and resumed). AutoGen's conversational model adds unnecessary degrees of freedom; a custom state machine's engineering cost is unjustifiable given LangGraph's fit.

The orchestration layer uses a thin adapter over LangGraph called `AgentRunner` that handles:
- Agent instantiation and tool injection
- Checkpoint persistence (to PostgreSQL via the `langgraph-checkpoint-postgres` integration)
- HITL pause/resume signaling
- Cost and token tracking per run
- Timeout enforcement (max wall-clock time per agent: 120s for assessment/debate, 300s for synthesis/curriculum)

### 4.3 Tool Access

Agents have access to a controlled, enumerated tool set. New tools require explicit review before being made available.

| Tool | Available to | Purpose | Rate limits |
|---|---|---|---|
| `search_collection` | All | Hybrid retrieval (§2.4) against a specified scope | 20 calls/agent-run |
| `fetch_chunk` | All | Retrieve a specific chunk by ID for citation resolution | Unlimited |
| `web_fetch` | Synthesis, Debate | Fetch a live URL (for sources flagged as web resources) | 5 calls/agent-run; robots.txt enforced |
| `calculator` | Assessment | Evaluate numeric expressions for quantitative questions | Unlimited |
| `code_executor` | Synthesis (opt-in) | Execute sandboxed Python for data analysis against structured sources | Disabled by default; operator opt-in |
| `entity_lookup` | All (full build) | Query knowledge graph for entity relationships (§6) | N/A (full build) |

The `code_executor` tool runs in a network-isolated sandbox (no outbound connections, ephemeral filesystem, 5s execution timeout). It is disabled by default because it expands the agent's attack surface and its outputs are harder to citation-ground than text generation. It is useful for collections containing structured data (CSVs, research datasets) where quantitative synthesis is required.

### 4.4 Human-in-the-Loop Checkpoints

Agents pause for human review at the following checkpoints, implemented as `interrupt()` nodes in LangGraph:

1. **Scope expansion confirmation:** When an agent determines it needs to query sources outside the user's originally specified scope (e.g., the synthesis query scoped to Collection A would benefit from Collection B), it pauses and presents the proposed expansion to the user before proceeding.
2. **Ambiguous query clarification:** When intent classification confidence is below 0.6 (the classification model assigns no single intent type a majority probability), the orchestrator surfaces the top-2 interpretations to the user and asks them to confirm intent before retrieval.
3. **Long-running job notification:** Jobs expected to exceed 60 seconds are surfaced to the user as async tasks with progress indicators; the user can cancel before completion.
4. **Assessment output review:** All quiz outputs are gated behind a user review step before publication to a shared collection. The user can reject individual questions; rejected questions are logged for evaluation dataset expansion.
5. **Debate agent scope confirmation:** Before a debate agent begins, the user must confirm the two poles being steelmanned to prevent unintended ideological framings.

---

## 5. Guardrails and Evaluation

### 5.1 Source Fidelity Scoring

Every generated response must be evaluated for faithfulness — the degree to which its claims are entailed by the cited source passages, rather than injected from the LLM's parametric knowledge. This is the core safety property of the platform.

**Implementation — NLI-based faithfulness scorer:**

1. For each sentence in the generated response that carries a citation, extract the cited chunks as premise.
2. Run an NLI (natural language inference) model (`cross-encoder/nli-deberta-v3-base` or equivalent) with the premise = cited chunks, hypothesis = generated sentence.
3. The model outputs a three-way label: `ENTAILMENT`, `NEUTRAL`, `CONTRADICTION`, and a confidence score.
4. Sentences labeled `NEUTRAL` (claim not supported by cited passages) or `CONTRADICTION` are flagged.
5. Compute a response-level fidelity score: the proportion of cited sentences labeled `ENTAILMENT` with confidence > 0.7.

Responses with fidelity score < 0.8 are subject to one of three actions depending on severity:
- Score 0.6–0.8: Add an inline warning to the UI ("Some claims in this response may not be directly supported by the cited sources").
- Score 0.4–0.6: Block the response and re-run generation with a stricter citation instruction.
- Score < 0.4: Block the response and surface an error to the user ("Unable to generate a reliably sourced response for this query").

Additionally, a hallucinated-citation check runs independently: every `chunk_id` in the response is verified against the context block IDs provided to the LLM. Any ID not in the context block is a hallucinated citation and immediately triggers a block-and-retry.

### 5.2 Confidence Calibration

The platform distinguishes two types of uncertainty that must be surfaced to the user differently:

**Retrieval uncertainty:** Did the retrieval step find strongly relevant passages, or did it return marginally related content? Measured by the cross-encoder score of the top-ranked chunk. If the top score is below 0.5, the system surface a "Low source coverage" warning: *"The available sources may not contain a reliable answer to this question."*

**Generation uncertainty:** Is the LLM generating a response it is confident about? For models that expose token-level log probabilities, a generation confidence score is computed as the mean log-probability of content tokens (excluding citation markup). Low mean log-probability correlates with hedging and confabulation. For models that do not expose log probabilities, a self-consistency probe is used: run the same prompt twice with temperature > 0 and compare the two responses via NLI similarity. High divergence signals low confidence.

Confidence signals are rendered to the user as:
- A visual indicator on the response card (not a percentage — research shows users over-anchor on percentage confidence figures).
- Inline flags on specific claims: "This claim is not directly supported by the retrieved passages."
- A "sources coverage" meter showing what fraction of the response's claims were matched to high-confidence passages.

### 5.3 Evaluation Harness

Every generation pipeline change (prompt update, model swap, retrieval parameter change) must pass an automated evaluation suite before deployment. The harness runs continuously in CI and on-demand.

**Evaluation datasets:**
- A human-curated gold-standard dataset of 500 query/answer pairs with ground-truth citations, sourced from a held-out subset of the platform's test corpus.
- A synthetic augmentation of 2,000 additional pairs generated by an independent LLM and verified by human spot-check (10% sample).

**Metrics computed on every generation:**

| Metric | Method | Target |
|---|---|---|
| Faithfulness | NLI-based (§5.1) | Mean score > 0.85 |
| Answer relevance | Cosine similarity between response embedding and query embedding | > 0.75 |
| Attribution accuracy | Fraction of response citations that point to a chunk containing the cited claim | > 0.90 |
| Context recall | Fraction of gold-standard answer tokens traceable to retrieved chunks | > 0.80 |
| Hallucinated citation rate | Fraction of responses containing at least one `chunk_id` not in the context block | < 0.005 |
| Latency P95 | Wall-clock time from query receipt to response delivery | < 5s (LOOKUP), < 15s (SYNTHESIS) |

A regression in any metric beyond a defined threshold (e.g., faithfulness drops > 0.03 from baseline) blocks the deployment.

**Tooling:** The evaluation harness is implemented using `RAGAS` (the open-source RAG evaluation framework) for faithfulness, relevance, and context recall metrics, augmented with custom evaluators for attribution accuracy and hallucinated-citation rate. Evaluation runs are logged to the platform's observability stack with per-metric history charts for trend detection.

### 5.4 Sensitive Content Handling

User-uploaded content may include private correspondence, internal research notes, proprietary documents, or personally identifiable information.

**At ingestion:** PII detection runs on all text before embedding, using a combination of regex patterns (email, phone, credit card, SSN formats) and a lightweight NER classifier for person names and organization names. Detected PII is not suppressed in storage (doing so would corrupt document meaning for legitimate professional use) but is flagged in chunk metadata (`pii_detected: bool`, `pii_types: list[str]`). This flag is used downstream to restrict sharing and prevent PII-bearing chunks from appearing in public or shared collection outputs.

**Isolation:** All user-uploaded content is scoped to the user's or team's private workspace by default (§7.1). It cannot appear in responses for other users' queries unless the user explicitly publishes the source to a shared collection.

**Content policy enforcement:** A classifier check runs on ingested text for content that violates platform policy (hate speech, CSAM, instructions for physical harm). Detected violations block ingestion and are reported to the platform's trust and safety queue. This is not a retrieval-time filter — it runs at ingestion to prevent policy-violating content from entering the index at all.

---

## 6. Knowledge Graph Layer

### 6.1 Rationale and Role

The vector store captures semantic proximity. The knowledge graph captures semantic structure: the fact that source A contradicts claim X from source B, that concept C is defined in source D and extended in source E, that entity F appears in seven sources with consistent characterization. This structural knowledge is not directly accessible to vector search — two chunks that are orthogonal in embedding space may have a critical inferential relationship that a graph can represent and traverse.

The knowledge graph is an overlay on the vector store, not a replacement. It is activated for queries that require relational reasoning and remains dormant for direct factual lookups where vector retrieval is sufficient.

### 6.2 Entity Extraction and Linking

Entities are extracted from chunks during ingestion using a two-stage process:

1. **NER pass:** A fine-tuned NER model extracts entities of types: `PERSON`, `ORGANIZATION`, `CONCEPT`, `EVENT`, `TERM` (technical definitions), `CLAIM` (propositional statements flagged as assertions). `CLAIM` is the most platform-specific entity type — it represents a sentence-level assertion that can be evaluated for support or contradiction across sources.

2. **Entity linking:** Extracted entities are linked to a canonical entity record using fuzzy string matching plus embedding similarity (to handle synonymy: "neural network" and "artificial neural network" should link to the same concept node). The entity linker maintains a per-collection entity dictionary. Cross-collection linking to a global entity namespace is a full-build feature.

### 6.3 Relationship Types

The platform defines four primary relationship types between chunk nodes in the graph:

| Relationship | Meaning | Example |
|---|---|---|
| `SUPPORTS` | Chunk A provides evidence that strengthens the claim in Chunk B | Two independent studies reaching the same conclusion |
| `CONTRADICTS` | Chunk A makes a claim that is incompatible with a claim in Chunk B | A study contradicting a previous study's findings |
| `EXTENDS` | Chunk A builds on or elaborates the idea introduced in Chunk B | A follow-up paper applying a method introduced in the cited paper |
| `DEFINES` | Chunk A provides a definition for a term used in Chunk B | A glossary entry that defines a term used in a primary source |

These relationships are inferred in two ways:
- **Heuristic extraction:** Citation parsing (when Source A explicitly cites Source B), cross-document entity co-occurrence at high frequency, and structural signals (a passage beginning with "However," after a claim-bearing passage is likely `CONTRADICTS`).
- **LLM-assisted inference:** For ambiguous cases, a batch classification job periodically samples chunk pairs with high entity overlap and asks a lightweight LLM to classify their relationship. This runs asynchronously, not at query time.

### 6.4 Graph-Augmented Retrieval

When the query planner identifies `query_entities` (§3.1), graph-augmented retrieval supplements the vector retrieval path:

1. Map each query entity to its canonical entity record.
2. Traverse the graph: retrieve chunks directly mentioning the entity, plus first-degree neighbors via `SUPPORTS`, `CONTRADICTS`, and `EXTENDS` relationships.
3. Merge graph-traversal results with vector retrieval results before the cross-encoder re-ranking step.
4. Annotate retrieved chunks with their relationship labels so the LLM can use relationship type in its citation framing ("Source A **contradicts** Source B's claim that ...").

The graph traversal is bounded to first-degree neighbors (depth-1) to control query latency. Second-degree traversal is available as an explicit opt-in for `SYNTHESIS` queries with `scope=GLOBAL`.

### 6.5 MVP Scoping Decision

The knowledge graph layer is a **full-build feature**. It is not included in the MVP for the following reasons:

- Entity extraction quality degrades on diverse, user-uploaded content without domain adaptation. Spurious entity linking creates misleading graph edges that erode user trust more than their absence.
- The relationship inference jobs introduce background processing complexity that competes with ingestion pipeline priorities.
- Vector retrieval with cross-encoder re-ranking provides strong results for the majority of queries without graph augmentation.

**What ships in MVP regarding the graph layer:** The entity extraction NER pass runs at ingestion and stores entity records in a relational table, but no edges are created, no graph queries are served. This provides the data foundation for graph construction without shipping unproven inference logic. The `CONTRADICTS` and `SUPPORTS` signal will be explicitly surfaced in the UI for source pairs where it is manually flagged by users — a community-grounded seed for the eventual automated inference.

---

## 7. Privacy and Data Architecture

### 7.1 Per-User and Per-Collection Isolation in the Vector Store

The platform's multi-tenancy model is: every source belongs to exactly one collection; every collection is owned by one user or team; visibility is controlled by an ACL table.

In pgvector, isolation is enforced via PostgreSQL row-level security (RLS). The `chunks` table carries `user_id` and `collection_id` columns. RLS policies are defined so that:
- A query issued in the context of user U only scans rows where `user_id = U` or where the `collection_id` is in U's `visible_collections` set (populated by the ACL service at query time).
- No application code can bypass this policy; it is enforced at the database session level.
- The platform never uses a single shared embedding query that cross-contaminates users' private collections with each other's data.

In the full-build migration to Qdrant, collection-level isolation is implemented via Qdrant's native collection namespaces, with one Qdrant collection per platform collection. This provides hard isolation at the vector store level rather than relying on row-level predicates.

**Service account credentials:** The application service account used for embedding storage has `SELECT`, `INSERT`, `UPDATE` on the `chunks` table, never `ALL PRIVILEGES`. A separate analytics service account with read-only access is used for evaluation jobs, preventing evaluation infrastructure from modifying the production index.

### 7.2 No Training on User Content Without Explicit Opt-In

This constraint is enforced at the architecture level through data plane separation, not through policy statements.

**Two data planes:**

1. **Private data plane:** All user-uploaded content, embeddings, and generated responses. This plane is write-only for ingestion and read-only for query serving. It is explicitly excluded from any data pipeline that feeds model training, fine-tuning, or evaluation dataset construction. The exclusion is enforced by a data flow control layer: the private plane's database cluster has no replication target pointing to any training data store. Granting a new replication target requires an infrastructure change with a mandatory security review gate.

2. **Training data plane:** Populated only from content where the user has explicitly opted in via a consent flag (`allow_training: bool`, default `false`) set at the source or collection level. The ETL job that populates the training data store includes a predicate `WHERE allow_training = true` that is part of the ETL definition, not an application-level filter. Even if application logic is bypassed, the ETL query itself excludes non-consented data.

**Audit log:** All reads from the private data plane are logged with `(user_id, source_id, chunk_id, query_timestamp, requesting_service)`. This log is immutable (append-only, no UPDATE or DELETE permissions on the log table) and is surfaced to users in a data access transparency dashboard.

### 7.3 Encryption at Rest and in Transit

**At rest:** Database volumes carrying the vector index and chunk text are encrypted using AES-256. For self-hosted deployments, Linux kernel-level LUKS full-disk encryption is the recommended approach — it requires no external service and adds negligible overhead. For deployments on managed infrastructure, volume encryption at the provider level is acceptable. Object storage (MinIO or local filesystem) uses server-side encryption configured at the MinIO level or filesystem-level encryption.

**In transit:** All internal service-to-service communication uses mutual TLS (mTLS) enforced by the service mesh. The embedding model inference endpoint (whether the self-hosted `nomic-embed` service or the external API) is accessed exclusively over TLS 1.3. No plaintext HTTP is permitted within the platform's network boundary; the ingress controller enforces HTTPS with HSTS headers and rejects downgrade requests.

**Key rotation:** Encryption keys are rotated on a 90-day schedule. Key rotation does not require re-encryption of stored data (the KMS envelope encryption model handles this transparently); it does require that all active service credentials are re-issued, which is automated via the secrets management service.

**Model inference isolation:** The self-hosted embedding model runs in a network-isolated pod with no outbound connectivity. It accepts only gRPC connections from the embedding service on a defined internal port. This prevents a compromised embedding worker from exfiltrating user content.

---

## 8. MVP vs Full Build

The MVP is defined by the principle: ship the retrieval-grounded citation engine as a working system for text-heavy sources (PDF, DOCX, web URLs) with strong attribution guarantees. Every other capability is layered on top.

### MVP (Version 1.0)

**Ingestion:**
- PDF, DOCX, web URL extractors (no OCR, no video, no audio, no structured data)
- Semantic chunking with 20% overlap; heading-path metadata
- SHA-256 content-hash de-duplication on re-ingestion

**Embedding and storage:**
- `nomic-embed-text-v1.5` self-hosted at 768 dimensions
- pgvector with HNSW index; RLS-enforced per-collection isolation
- Hybrid retrieval (dense + BM25 sparse) with RRF fusion
- Cross-encoder re-ranking (`ms-marco-MiniLM-L-6-v2`)

**RAG:**
- Intent classification (4-class: LOOKUP / SYNTHESIS / COMPARISON / GENERATION)
- Single-hop retrieval for LOOKUP and COMPARISON; two-hop retrieval for SYNTHESIS
- Inline citation format with chunk-ID resolution at render time
- Hallucinated-citation detection (chunk-ID validation post-generation)

**Agents:**
- Synthesis Agent (available to all users, collection-scoped)
- Assessment Agent (quiz generation, gated behind human review before publish)
- LangGraph orchestration; PostgreSQL checkpoint persistence

**Guardrails:**
- NLI-based faithfulness scorer; fidelity < 0.8 triggers warning or block
- Retrieval uncertainty indicator (low source coverage warning)
- PII detection flag on ingested chunks
- Content policy classifier at ingestion

**Privacy:**
- Two-data-plane separation (private vs training); `allow_training` flag defaults to false
- AES-256 at rest; TLS 1.3 in transit; audit log (append-only)
- RLS per-user/per-collection in pgvector

**Not in MVP:** Video/audio ingestion, OCR for scanned PDFs, structured data (CSV/JSON) ingestion, image visual descriptions, CLIP multimodal embeddings, multi-hop > 2 hops, Curriculum Agent, Debate Agent, Knowledge Graph layer (entity extraction runs but produces no graph edges), Qdrant migration, CMEK key management.

### Full Build (Version 2.0 and beyond)

**Ingestion additions:** YouTube transcript extraction + Whisper audio transcription; OCR for scanned PDFs (Tesseract); CSV/JSON verbalized ingestion; image OCR + vision-model description; speaker diarization for audio.

**Embedding additions:** CLIP/SigLIP multimodal embedding for images with a separate image-vector index; alternative open-source embedding models (e.g., `BGE-M3`, `multilingual-e5-large`) as operator-selectable alternatives via the embedding adapter interface.

**Storage migration:** Qdrant for deployments exceeding ~20M chunks; per-collection namespace isolation; payload filtering at the vector DB level.

**RAG additions:** Multi-hop > 2 (with agent handoff); map-reduce synthesis for very large corpora; generation confidence via self-consistency probe for models without log-probability access.

**Agents additions:** Curriculum Agent (learning path sequencing); Debate Agent (steelman mode); `code_executor` tool (operator opt-in for quantitative synthesis over structured data).

**Knowledge Graph:** NER entity extraction producing live graph edges; LLM-assisted relationship inference batch jobs; `SUPPORTS`/`CONTRADICTS`/`EXTENDS`/`DEFINES` relationship types; graph-augmented retrieval with depth-1 traversal; second-degree traversal for SYNTHESIS/GLOBAL queries.

**Privacy additions:** CMEK per-enterprise-tenant with customer-managed key rotation; data access transparency dashboard surfaced in user settings; granular consent controls at source level (not just collection level).

**Evaluation harness expansion:** Continuous regression on RAGAS metrics; per-agent evaluation pipelines (curriculum coherence score, assessment answer traceability score); evaluation dataset growth via user-flagged response quality signals.