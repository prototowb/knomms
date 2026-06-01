# Platform Vision — Knowledge Commons

## The Single Platform

Knowledge Commons is a **grounded collective intelligence platform**: a place where any person or community can build, share, and learn from living knowledge bases that the AI reasons over — not around.

The critical distinction from adjacent products: the AI is not a feature layer on top of content management. It IS the content model. Sources are not things you "ask AI about" as a side function — they are the semantic substrate the platform reasons from, cites, and synthesizes across every layer.

---

## Three Layers, One Platform

### Layer 1 — Grounded Knowledge Core

Any collection of sources (documents, video transcripts, images, URLs, notes, audio) is ingested, normalized, and stored as a **grounded knowledge base** — a private or shared corpus the AI can query, synthesize, and cite with provenance.

The core contract: **every AI output is anchored to specific source passages with attribution**. The system reasons, but every claim must trace back to ingested material. This is the integrity guarantee that makes the platform trustworthy for serious knowledge work.

Capability primitives:
- Multimodal ingestion and semantic normalization
- Retrieval-Augmented Generation with passage-level citation
- Cross-collection semantic search
- Agentic synthesis (AI agents that compile, summarize, compare, debate)
- Confidence and attribution scoring on all outputs

### Layer 2 — Structured Learning Layer

The learning layer is not a course authoring tool. It is a **transformation agent** that operates on knowledge bases: given a corpus, it generates structured learning paths, assessments, progress milestones, and comprehension checks. These are first-class artifacts derived from the core — not a separate content type.

Every lesson and every assessment answer links back to source passages. Assessment answers are checkable against the source, not just graded against a key.

Capability primitives:
- AI-generated learning path proposals from a corpus
- Assessment generation grounded in source content
- Progress and comprehension tracking
- Cohort learning: shared knowledge base + individual progress
- Instructor review and override on all AI proposals

### Layer 3 — Discovery and Curation Layer

Discovery is the social, visual front-door: people browse, save, remix, and fork curated collections. Collections are visual boards — spatial and media-rich, not folder trees. Every item in a board is a source that feeds a knowledge base.

Serendipity is AI-powered: the system surfaces collections that semantically overlap with your current knowledge bases, driven by embedding proximity, not engagement metrics.

Capability primitives:
- Visual board browsing with rich media cards
- Fork/remix: clone a public collection as the seed of a private knowledge base
- AI-powered collection recommendations based on semantic proximity
- Social graph: follow curators, see what they're building
- Visibility controls: private / team-shared / public-read / public-forkable

---

## Community as Connective Tissue

Community is not a fourth layer — it permeates all three:
- Knowledge bases can be **co-authored** (collaborative corpus building)
- Learning paths can be **cohort-shared** (same corpus, individual progress)
- Collections can be **forked with attribution** (remix lineage, contributor credit)
- Discussions are **grounded** (replies cite source passages, not floating opinion)

Social actions (share, fork, follow, discuss) are always connected to knowledge artifacts, not a disconnected feed.

---

## AI Architecture Principles

These are non-negotiable constraints, enforced architecturally:

1. **Retrieval before generation** — No free-form generation without a retrieval step anchoring the output
2. **Attribution as data** — Citation/provenance is a first-class field on every AI-generated artifact
3. **Multimodal parity** — Text, images, audio/video, and structured data are equal citizens in the ingestion pipeline
4. **Agentic, not just Q&A** — The AI can propose, compile, compare, generate assessments, and assemble learning paths
5. **Evals baked in** — Source fidelity scoring, confidence intervals, and human-feedback loops from day one
6. **Privacy by default** — Knowledge bases are private until explicitly published; no training on user content without opt-in

---

## What This Is Not

- Not a general-purpose chat assistant (no free-floating responses without grounded retrieval)
- Not a document storage or CMS (the AI relationship to content is mandatory, not optional)
- Not a MOOC platform (learning paths are outputs of the AI, not the primary content model)
- Not a social media feed (virality is not a design goal; depth and trust are)

---

## The Design Bets

**Bet 1: Grounding earns trust.** In a world of AI-generated noise, a platform that can always show you exactly which source passage supports each claim will earn disproportionate trust from people doing serious knowledge work.

**Bet 2: Curation is undervalued labor.** The act of assembling a high-quality source collection is knowledge work in itself. Making that work shareable, forkable, and visible through the platform creates an incentive to curate well.

**Bet 3: Learning paths derived from primary sources are better than content-as-product.** Learners who can always jump from a lesson explanation to the underlying source passage develop stronger knowledge than those consuming purpose-built educational content divorced from primary material.

**Bet 4: Semantic discovery beats engagement-optimized discovery.** Recommending collections based on what your corpus means — not on what users who look like you clicked — produces more useful serendipity with less epistemic manipulation.
