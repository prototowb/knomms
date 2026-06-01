# Product Specification — Knowledge Commons

**Version:** 0.1  
**Status:** Draft — pre-development

---

## 1. Core Personas

### 1.1 Self-Directed Learner

**Profile:** An individual assembling their own knowledge base — uploading papers, documentation, transcripts, or notes — and using the platform to structure their own learning without needing an external instructor.

**Core need:** "I collect knowledge obsessively. I need help turning my collection into something I actually understand and retain."

**Representative flows:**
- Upload 12 research papers → state a learning goal → receive an AI-generated structured path through those papers with comprehension checks
- Ask questions against their own corpus and get cited, grounded answers
- Browse public collections, fork one that covers a topic they're exploring, have it automatically become a queryable knowledge base

**What the platform does that nothing else does:** The learner does not need to know how to structure learning. They collect knowledge; the AI derives the curriculum. Their only authoring act is corpus assembly.

---

### 1.2 Instructor / Curator-Educator

**Profile:** An educator, subject-matter expert, or trainer assembling a corpus to teach a cohort.

**Core need:** "I want to teach from primary sources, not purpose-built courseware. I want AI to do the production work while I focus on pedagogy and judgment."

**Representative flows:**
- Build a source collection, invoke the AI curriculum agent with a learning goal and time budget, receive a full course proposal
- Review and override individual lesson explanations; annotate over AI-generated content where needed
- Set mastery thresholds, publish to a cohort, monitor comprehension heatmaps, and add sources to address detected misconceptions

**What the platform does differently:** The instructor's contribution is curation, selection, and judgment — not authoring content from scratch. Every lesson explanation traces back to sources the instructor chose.

---

### 1.3 Student / Cohort Learner

**Profile:** An enrolled learner consuming an instructor-shaped course.

**Core need:** "I want to understand this material, not just pass the assessment. I want to be able to go deeper when something interests me."

**Representative flows:**
- Progress through a learning path with inline citations that can be opened to the source passage
- See grounded feedback on wrong assessment answers ("The correct answer is stated in [Source, Section 3.2]")
- Post a discussion anchored to a specific passage; see other students' annotations on that passage
- Have a spaced repetition queue surface concepts before they're forgotten

---

### 1.4 Research Team / Professional Team

**Profile:** A team building a shared knowledge base from internal documentation, ADRs, runbooks, and external references.

**Core need:** "New team members take months to reach operational baseline. Our docs exist but nobody reads them. We need a way to make the docs learnable."

**Representative flows:**
- Designate a subset of the team's shared knowledge base as the onboarding corpus
- Invoke the AI curriculum agent with: "new engineer understands our data flow and operational procedures, 2-week ramp"
- Enroll new team members; their comprehension checks test against the team's actual runbooks
- When a runbook is updated, affected learning path concepts enter a "stale — needs review" state automatically

**What the platform does differently:** The learning path is derived from the team's own living documentation. It doesn't go stale independently — it goes stale when and only when the source docs change.

---

### 1.5 Knowledge Curator (Discovery Layer)

**Profile:** Someone who builds and publishes high-quality source collections for others to discover and fork.

**Core need:** "I want my curation work to be visible and reusable. I want people to build on what I've assembled."

**Representative flows:**
- Build a board of 15 sources on urban heat policy — papers, legislation, datasets, transcripts
- Receive an AI-generated board overview that notes coverage gaps
- Publish the board; watch it get forked by researchers and students
- See attribution maintained as forks build upon the original

---

## 2. Capabilities by Layer

### 2.1 Layer 1 — Grounded Knowledge Core

| Capability | Description |
|---|---|
| Multimodal ingestion | PDF, web pages, video (transcript), audio, images (OCR + caption), CSV/JSON, code files |
| Semantic chunking | Source text split into addressable, citable passage units with locator metadata (page, timestamp, paragraph) |
| Vector embedding | Passages embedded for semantic search; model version tracked per knowledge base |
| Hybrid retrieval | Dense (vector) + sparse (BM25) retrieval with cross-encoder reranking |
| Grounded Q&A | Questions answered with responses citing specific passage IDs and locators |
| Agentic synthesis | Multi-hop agents: synthesize themes across sources, compare positions, steelman arguments |
| Knowledge graph overlay | Entity extraction, relationship typing (supports / contradicts / extends / defines), graph-augmented retrieval |
| Source fidelity scoring | Drift detection between generated responses and cited source passages |
| Privacy isolation | Per-knowledge-base namespace isolation enforced at the vector query layer |

### 2.2 Layer 2 — Structured Learning Layer

| Capability | Description |
|---|---|
| AI curriculum proposal | Concept extraction, prerequisite graph inference, sequence generation from any corpus |
| Grounded explanations | Every concept explanation contains inline citations to source passages |
| Assessment generation | Multiple-choice (with grounded distractors), open-ended (with passage-grounded rubric), source retrieval questions |
| Instructor review interface | Accept, override, reorder, prune, or extend AI-proposed concepts |
| Grounded assessment feedback | Wrong-answer feedback cites the specific passage that clarifies the misconception |
| Spaced repetition | Per-learner forgetting-curve scheduling for concept review |
| Mastery gates | Configurable thresholds; progression blocked until mastery is demonstrated |
| Cohort enrollment | Shared corpus, individual progress tracks |
| Passage-anchored discussion | Discussion threads anchored to source passages, not to lesson pages |
| Comprehension heatmaps | Instructor analytics: which concepts have low mastery, which distractors are most chosen |
| Corpus change propagation | When a source is updated, affected learning path concepts flag as stale |
| Path versioning | Version-controlled learning paths with learner progress migration |

### 2.3 Layer 3 — Discovery and Curation Layer

| Capability | Description |
|---|---|
| Visual collection boards | Board-style spatial layout; swim-lane mode and free-form canvas mode |
| Rich media cards | Thumbnail, title, author, excerpt, source type badge |
| Fork/remix | Clone any public board as the seed of a private knowledge base; triggers ingestion |
| Fork lineage attribution | Multi-level ancestry tracking with curator credit |
| Semantic recommendations | AI-powered: boards adjacent to your current corpus based on embedding proximity |
| Cross-collection search | Semantic search across all public boards and sources |
| Curator profiles | Published boards, inferred expertise signals (derived from corpus content, not self-reported) |
| Grounded comments | Comments must be anchored to a specific source card or quoted passage |
| Gap analysis | AI identifies thematic gaps, perspective imbalances, and source-type skew in a board |
| Auto-tagging | AI proposes concept tags and swim-lane placement for newly added sources |
| Board summary generation | AI-written overview noting both coverage and notable gaps |
| Opt-in fork sync | Board owners can notify fork owners of updates; sync is always explicit |
| Mobile capture | Photo → OCR → source card entry point on mobile |

---

## 3. Cross-Cutting Capabilities

| Capability | Description |
|---|---|
| Visibility controls | Private / team-shared / public-read-only / public-forkable on all major entities |
| Team workspaces | Shared collections and knowledge bases for an organization; collaborative co-authorship |
| Developer API | REST API with citation arrays on all generation responses; webhooks for key events |
| Custom ingestion adapters | Third-party developers can register custom source type adapters |
| Audit-quality attribution | Every AI output carries full provenance: chunk ID, source ID, locator, version hash |

---

## 4. Key User Journeys

### Journey A: Research Sprint (Self-Directed Learner)

```
1. User uploads 8 PDF papers and 3 web articles on a topic
   → Each source is ingested, chunked, embedded (background, ~2 min total)

2. User asks: "What are the main competing positions on X?"
   → AI synthesizes a grounded overview citing specific passage locators from 6 of the 11 sources
   → User can click any citation to read the original passage in a side panel

3. User requests a learning path: "Help me understand this topic in depth over 3 hours"
   → AI curriculum agent proposes 4 modules, 11 concepts, 23 assessment items
   → User reviews the proposal, collapses one module as already known, publishes to self

4. User works through the path over 3 sessions
   → Spaced repetition queue surfaces 5 review items before each session
   → On a wrong answer: "The correct answer is stated in [Paper 3, p. 7]: '...'"

5. User adds 2 new papers discovered mid-way through
   → System notifies: "3 concepts in your active path now have additional source material"
   → User accepts suggested explanation regeneration for 2 of those concepts
```

### Journey B: Instructor Builds a Course

```
1. Instructor builds a team corpus (20 sources) and invokes the curriculum agent:
   Learning goal: "Students understand distributed consensus algorithms"
   Time budget: 6 weeks, part-time
   Audience: software engineers, no distributed systems background assumed

2. Agent proposes: 5 modules, 18 lessons, 54 concepts, full assessment bank
   → Instructor reviews module by module
   → Accepts 12 concepts as-is, overrides 4 explanations (tone wrong for audience),
     prunes 2 modules outside scope, requests a re-proposal for Module 3

3. Instructor sets mastery thresholds:
   Modules 1-3: gate required (0.75 threshold)
   Modules 4-5: soft gate (warning, but not blocked)

4. Instructor publishes to cohort of 30 students

5. After 2 weeks:
   → Comprehension heatmap shows Concept "Raft leader election" has 34% mastery
   → Misconception report: 18 students chose distractor "leader is elected by clients"
   → Instructor adds 2 clarifying passages to the corpus
   → Triggers explanation regeneration for that concept
   → Students who already passed it are unaffected; students in progress see updated explanation

6. At course end:
   → Instructor exports cohort comprehension report
   → Publishes the collection (source board) publicly so others can fork and teach from it
```

### Journey C: Discovery and Fork (Curator → Learner)

```
1. New user lands on Discovery feed
   → Sees trending boards, semantically matched to their stated interests

2. Clicks "Agroecology Systems" board by @dr.okonkwo
   → 14 source cards in 3 swim lanes; board summary notes coverage and one gap
   → Curator annotations visible on 10 of 14 cards

3. User clicks "Fork this board"
   → Private KB created; 14 sources queued for ingestion
   → 8 sources from shared cache: ready immediately; 6 new: ~4 min to index

4. User adds 3 of their own sources to the fork
   → Board updates; new sources are ingested and embedded into the KB

5. User asks their first question against the fork
   → Cited answer draws from both the original 14 sources and their 3 additions
   → Attribution shows: "From [original curator's source] + [your source]"

6. User requests a learning path
   → 17-source corpus → AI proposes a structured 4-hour path
   → Path attribution notes that the corpus was seeded from @dr.okonkwo's board
```

---

## 5. Non-Goals and Open Questions

### Non-Goals

- General-purpose AI chat (the AI cannot respond without grounded retrieval)
- Document storage / file management (sources are not managed as files; they are semantic corpora)
- Social media virality (engagement optimization is not a design goal)
- Video production or interactive lesson authoring (the learning layer is text-and-citation; rich media production is out of scope)
- Real-time collaborative document editing (knowledge bases are collaborative, not simultaneous co-editors of a document)

### Open Questions

1. **Multimodal image reasoning depth:** At MVP, images are OCR + caption. Full visual reasoning (interpreting charts, diagrams) requires a multimodal generation model in the retrieval path — what's the right timing to introduce this?

2. **Paywall/DRM sources:** How to handle sources the platform cannot fully ingest (paywalled articles, DRM PDFs)? Options: user-provided full text, excerpt-only with source link, or blocked with a notice.

3. **Sensitive/confidential corpora:** Enterprise teams will want to use internal documents that should never be accessible outside the org. This requires isolated infrastructure (dedicated vector store namespace with additional network-level isolation) — when does this tier ship?

4. **AI model substitution:** The platform's grounding contract works across generation model families (the citation mechanism is model-agnostic). But the quality of concept extraction and curriculum generation varies significantly across models. Should the platform expose model selection to power users or lock to a house model?

5. **Trust and moderation at scale:** What is the governance model for public boards? A board with high fork counts becomes an influential epistemological artifact. Who reviews it for accuracy? What are the mechanisms for community correction?

6. **Institutional/academic partnerships:** Could the platform ingest pre-cleared academic library collections? This would seed a high-quality public corpus but requires licensing negotiation outside the platform's core scope.
