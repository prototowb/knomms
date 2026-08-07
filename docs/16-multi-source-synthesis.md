# Multi-Source Synthesis, Part 1 — Design (V2 roadmap #3)

> Status: **proposed** (2026-08-07). First slice of the roadmap's #3 V2
> priority ("Multi-hop synthesis agents — 'Compare these three sources on
> topic X' with multi-document citation", `docs/06-roadmap.md` §V2). This
> part ships the roadmap's own example: **comparative synthesis across
> user-selected sources in one grounded generation pass**. Iterative
> hop loops (decompose → retrieve → reason → retrieve again) stay in part 2.
> Proposed sprint: **v0.13.0 = KC-096–098**.

## 1. Problem

Q&A retrieves the globally nearest chunks — ask a KB with three papers
"how do these sources differ on X?" and retrieval happily returns all
`top_k` chunks from one paper, and the model, correctly, answers from that
one. There is no way to force representation from *each* source, and no
prompt contract that asks for comparison rather than answer-lookup. The
comparative question is the single most common multi-document task and it
falls out of one retrieval change plus one prompt.

## 2. Why one pass (not an agent loop)

True multi-hop (sub-query decomposition, chained retrievals) multiplies
LLM rounds; on the reference CPU hardware one generation is ~2 minutes,
so a 3-hop loop is a ~10-minute query with no intermediate value shown.
Balanced retrieval + a comparison prompt delivers the roadmap's example
in one round, streams like existing Q&A, and reuses the citation validator
unchanged. When GPU deployments are the norm (or part 2 adds progress
events per hop), the loop becomes worth its latency.

## 3. Design decisions

| # | Decision | Call | Rationale |
|---|---|---|---|
| OQ-63 | Part-1 shape | Selected-source comparative synthesis: `POST /v1/kbs/{kb_id}/synthesize` with `{question, source_ids: [2–5]}`, streaming SSE | The roadmap's own example, CPU-honest (one generation), and the retrieval balance is the real gap — an agent loop without balanced retrieval still compares one source with itself |
| OQ-64 | Balanced retrieval | `retrieve()` gains an optional `source_id` filter; the service retrieves `chunks_per_source` (settings, default 2) nearest chunks *per selected source* — every source is represented or explicitly absent | Global top-k is the failure mode (§1). Per-source scoping reuses the HNSW index with one extra WHERE. Default 2×N chunks keeps CPU prefill tolerable (`SYNTHESIS_CHUNKS_PER_SOURCE`, GPU raises it) |
| OQ-65 | Authz + validation | Readable-KB predicate (same as query); every `source_id` must belong to the KB → 422 otherwise (ids are not secret inside a readable KB); 2–5 sources; sources with zero embedded chunks are reported in the answer preamble, not errors | Reuses the only correct read relaxation; a cross-KB source id must not leak chunks from another namespace — the KB check plus namespace-scoped retrieval enforces this twice |
| OQ-66 | Prompt contract | Passages grouped under `--- SOURCE: {title} ---` headers; instructions demand a comparison (agreements, disagreements, unique claims) with `[SOURCE:chunk_id]` on every claim — the existing citation notation | The validator, SSE citations event, and frontend citation rendering all key on the existing notation; the only new thing the model sees is grouping + task framing |
| OQ-67 | SSE contract | Byte-identical event shapes to Q&A (`event: citations` first, then token events) | `useStreamingQuery` is reused with a different endpoint — no new frontend streaming code |
| OQ-68 | Surface | "Compare" tab on the KB workspace: source multi-select (embedded sources only), question input, streamed answer with the existing citations sidebar | Tab precedent (OQ-5); no new route. Boards/explore untouched in part 1 |

## 4. Backend changes

- `retrieval/service.py`: optional `source_id: str | None` filter on
  `retrieve()` (adds `Chunk.source_id == source_id` to the WHERE).
- **New** `generation/synthesis.py`:
  - pure `build_synthesis_prompt(question, groups)` — groups are
    `(source_title, chunks)` pairs; §3 OQ-66 contract.
  - `SynthesisService.stream_synthesis(kb_id, question, source_ids, user)`:
    readable-KB check, source membership check (422), per-source retrieval
    via the query embedding, empty-source preamble, then the same
    citations-event + token-stream generator as Q&A (semaphore shared).
- Router: `POST /v1/kbs/{kb_id}/synthesize` (SSE), mirroring the query
  endpoint's shape; registered before `/{kb_id}` param routes as needed.
- `core/config.py`: `synthesis_chunks_per_source` (default 2).
- Tests: prompt-builder shape (grouping, headers, citation instructions),
  source-membership guard decision, per-source balance math.

## 5. Frontend changes

- KB workspace gains a **Compare** tab: checkbox list of embedded sources
  (2–5 enforced client-side too), question input, streamed response via
  `useStreamingQuery`'s pattern pointed at the synthesize BFF route,
  citations sidebar reused as-is.
- BFF: `server/api/kb/[kbId]/synthesize.post.ts` streaming proxy (same
  pattern as the query route).

## 6. Non-goals (part 2 candidates)

- Iterative hop loops with per-hop progress events (OQ-63)
- Cross-KB synthesis (retrieval is namespace-scoped by design)
- Saving/sharing synthesis results as artifacts or board items
- Automatic source selection ("compare everything relevant")

## 7. Verification plan (KC-098)

1. Unit: prompt grouping/headers/instructions; membership-guard and
   balance-math helpers.
2. Live (Colima): KB with ≥2 embedded sources (a web page + the v0.12.0
   video) → synthesize over both: citations event lists chunks from both
   sources, answer streams, per-source citation ids validate; foreign
   source id → 422; <2 or >5 sources → 422; non-readable KB → 404;
   Compare tab renders sources and streams in the browser.
3. Regression: Q&A endpoint untouched (same events); full pytest; vue-tsc.
