# Knowledge Comms — Layer 2: Structured Learning Layer

## Product + Technical Specification v0.1

---

## 1. Core Concept: The Learning Layer as AI Output

### 1.1 The Fundamental Distinction

A traditional learning management system is a container. An author creates content and deposits it. The AI, if present, is a bolt-on. The knowledge and its structure are both human-authored artifacts.

The Structured Learning Layer rejects this model. It is a **transformation agent**: given a corpus of grounded source material living in the Knowledge Core, it proposes, generates, and continuously revises a structured learning experience from that corpus. No human author writes lesson content. The AI reads the corpus, reasons about its structure, identifies concepts and dependencies, proposes a learning sequence, and generates all explanatory content — with every claim traceable back to a specific passage in a source document.

The key inversion: in LMS thinking, you first author a course, then attach it to content. In transformation agent thinking, you first assemble a grounded knowledge base, then the agent derives the course from it. The corpus is primary. The learning experience is derivative.

This has a decisive practical consequence: **a lesson without a cited source passage is not a valid lesson**. It is a schema violation. The data model enforces this. The agent cannot generate curriculum in a vacuum; it can only generate curriculum the corpus supports.

### 1.2 The AI-Generated Learning Path Proposal

When an instructor or self-directed learner points the learning layer at a corpus, the **Curriculum Agent** performs:

1. **Corpus indexing**: retrieve all source passages, grouped by document and concept cluster
2. **Concept extraction**: identify distinct concepts addressable in isolation
3. **Prerequisite inference**: determine which concepts must be understood before others
4. **Sequence construction**: topologically sort the prerequisite graph; apply pacing heuristics
5. **Explanation generation**: generate concept explanations grounded in and citing source passages
6. **Assessment generation**: generate assessment items whose correct answers are verifiable against sources

The output is a **learning path proposal** the instructor can inspect, accept, reject, reorder, or annotate.

#### Example agent prompt (pseudocode level)

```
SYSTEM:
You are a curriculum agent operating on a grounded knowledge base.
You may only generate content directly supported by the source passages provided.
Every concept you propose must cite at least one source passage by passage_id.
Every explanation must contain inline citations using [passage_id] notation.
You cannot introduce claims not present in the corpus.

INPUT:
  corpus_passages: [{ passage_id, document_title, section, text, embedding }]
  learning_goal: "Understand the end-to-end request lifecycle in a distributed cache system"
  time_budget_hours: 4
  prior_knowledge_signals: ["learner has completed Module: Networking Fundamentals"]

TASK:
1. Extract all concepts addressable from this corpus relevant to the learning goal.
2. For each concept, identify prerequisite concepts (within this corpus only).
3. Propose a module/lesson/concept hierarchy fitting the time budget.
4. For each concept node produce: concept_title, explanation (inline citations required),
   source_passage_ids, prerequisite_concept_ids, assessment_items.
5. Output JSON matching the LearningPathProposal schema.

CONSTRAINT: If the corpus does not contain enough material to justify a concept, omit it.
Do not pad the path with inferred knowledge not present in the corpus.
```

### 1.3 The Human Instructor Role

The agent's proposal is a starting point. Instructors can:

- **Accept** a module, lesson, or concept node as-is
- **Override** the AI-generated explanation with their own text (annotation stored separately; citation links remain)
- **Reorder** lessons or concepts (system warns if the new order violates a prerequisite dependency)
- **Prune** a concept (removes it and any downstream concepts depending solely on it)
- **Extend** by adding a new concept node — but the system requires selecting at least one source passage from the corpus to anchor it; freeform content without a citation is blocked at the data layer
- **Request a re-proposal** after editing the corpus or adjusting parameters; the system diffs the new proposal against the current version

### 1.4 The Grounding Contract

> Every concept explanation contains at least one inline citation linking to a source passage.  
> Every assessment item's correct answer carries a `grounding_passage_id`.  
> Every distractor carries a `why_wrong_passage_id` pointing to a passage that clarifies the misconception.  
> No content field in the learning path schema accepts a non-null value unless a citation accompanies it.

This is enforced at write time by the data layer, not by convention. A lesson record that fails grounding validation does not persist.

---

## 2. Personas and Use Cases

### 2.1 Self-Directed Learner

Assembles their own corpus, uses the platform to structure their own learning without an external instructor.

**Core flow:** Upload papers → state learning goal → receive AI-generated path → work through concepts with grounded feedback → add new documents mid-way → system notifies which concepts now have additional source material.

**The transformation agent unlocks something an LMS cannot:** the learner does not need to know how to structure learning. They collect knowledge; the agent derives the curriculum.

### 2.2 Instructor

Assembles a corpus to teach a cohort.

**Core flow:** Create course corpus → invoke curriculum agent with learning goal, target audience, time budget → review proposal module by module → accept/override/prune → set mastery thresholds → publish to cohort → monitor comprehension heatmaps → add sources to address detected misconceptions.

**What the instructor does not do:** write lesson content from scratch. The instructor's intellectual contribution is selection, curation, and judgment — not authoring.

### 2.3 Student in a Cohort

**Core flow:** Progress through a published learning path → read AI-generated concept explanations with visible inline citations → complete comprehension checks with grounded feedback on wrong answers → post discussion threads anchored to specific passages → see aggregate comprehension signals from cohort.

### 2.4 Professional Team

Uses the platform to onboard new team members from the team's own living documentation (runbooks, ADRs, architecture docs).

**The unique value:** the learning path is derived from the team's actual documentation. It doesn't go stale independently — it goes stale when and only when the source documentation changes, and the system surfaces that staleness.

---

## 3. Learning Path Data Model

### 3.1 Unit Hierarchy

```
LearningPath
  ├── id: uuid
  ├── corpus_id: uuid
  ├── learning_goal: string
  ├── version: integer
  ├── status: draft | published | archived
  ├── time_budget_hours: float
  ├── modules: Module[]
  └── prerequisite_graph: ConceptGraph

Module
  ├── id: uuid
  ├── title: string
  ├── summary: string
  ├── summary_citations: PassageCitation[]  (REQUIRED, min 1)
  ├── position: integer
  ├── lessons: Lesson[]
  └── mastery_threshold: float (default 0.8)

Lesson
  ├── id: uuid
  ├── title: string
  ├── position: integer
  ├── estimated_minutes: integer
  └── concepts: Concept[]

Concept
  ├── id: uuid
  ├── title: string
  ├── ai_explanation: ExplainedContent     (REQUIRED)
  ├── instructor_annotation: Annotation | null
  ├── source_passages: PassageCitation[]   (REQUIRED, min 1)
  ├── prerequisite_concept_ids: uuid[]
  └── assessment_items: AssessmentItem[]   (min 1)
```

### 3.2 Core Sub-Types

```
ExplainedContent
  ├── text: string                   (inline [passage_id] citations required)
  ├── generated_at: timestamp
  ├── agent_version: string
  └── passage_ids_cited: uuid[]      (denormalized from inline citations)

PassageCitation
  ├── passage_id: uuid
  ├── document_id: uuid
  ├── document_title: string
  ├── section_label: string | null
  ├── excerpt: string
  └── relevance_note: string | null
```

### 3.3 Assessment Items

```
AssessmentItem
  ├── id: uuid
  ├── question_type: multiple_choice | open_ended | source_retrieval
  ├── question_text: string
  ├── grounding_passage_id: uuid      (REQUIRED for all types)
  ├── correct_answer: string          (for MC and source_retrieval)
  ├── rubric: OpenEndedRubric | null  (REQUIRED for open_ended)
  └── distractors: Distractor[]       (REQUIRED for MC, min 2)

Distractor
  ├── text: string
  ├── why_wrong_passage_id: uuid
  └── misconception_label: string | null
```

#### Example concept node (abbreviated JSON)

```json
{
  "id": "c1a2b3",
  "title": "Write-ahead logging as durability guarantee",
  "ai_explanation": {
    "text": "Write-ahead logging (WAL) ensures durability by recording every intended change to a persistent log before applying it to the data store [p-4421]. If the system crashes mid-write, the recovery process replays the log from the last checkpoint [p-4422].",
    "passage_ids_cited": ["p-4421", "p-4422"]
  },
  "source_passages": [
    {
      "passage_id": "p-4421",
      "document_title": "Distributed Storage Internals",
      "section_label": "Section 4.3 — Crash Recovery",
      "excerpt": "The write-ahead log records each change before it is applied..."
    }
  ],
  "assessment_items": [
    {
      "question_type": "multiple_choice",
      "question_text": "What is the primary purpose of the write-ahead log in crash recovery?",
      "grounding_passage_id": "p-4421",
      "correct_answer": "To ensure no committed transaction is lost by recording changes before they are applied",
      "distractors": [
        {
          "text": "To compress the data store for faster reads",
          "why_wrong_passage_id": "p-4421",
          "misconception_label": "conflates logging with compression"
        }
      ]
    }
  ]
}
```

### 3.4 Prerequisite Graph

```
ConceptGraph
  ├── nodes: ConceptNode[]
  └── edges: PrerequisiteEdge[]

PrerequisiteEdge
  ├── from_concept_id: uuid          (must be understood before...)
  ├── to_concept_id: uuid            (...this concept)
  ├── strength: required | recommended
  └── agent_rationale: string
```

The prerequisite graph is stored separately from the lesson hierarchy so learners who test out of concepts can have individual progress states resolved against the graph without altering the authored sequence. Cycles are rejected at write time.

---

## 4. Assessment and Comprehension

### 4.1 Question Types

**Multiple-choice (MC):** One correct answer with 2–4 distractors. On answer reveal, the learner sees the passage excerpt supporting the correct answer, and a note on why each distractor is wrong — sourced from passages, not freeform AI commentary.

**Open-ended (OE):** Free-text response. Graded against a passage-grounded rubric by semantic verification (see §4.2).

**Source retrieval (SR):** The learner is shown a question and must locate — by selecting within the source corpus — the passage that best answers it. Example: "Find the passage that explains how checkpointing limits log replay size." This trains reading primary sources directly and is unique to grounded platforms.

### 4.2 Grounded Answer Verification for Open-Ended Questions

```
SYSTEM:
You are an answer evaluator for a grounded learning platform.
You may only evaluate a learner's answer against the provided source passages and rubric.
You cannot award credit for a claim correct in general but absent from the cited passages.
You cannot penalize a claim correct and present in the cited passages, even if the rubric missed it.

INPUT:
  question_text, learner_answer, grounding_passage: { passage_id, text }
  rubric: { key_claims: [], acceptable_answer_summary, negative_indicators: [] }

OUTPUT:
  claim_scores: [{ claim, score, learner_excerpt, passage_excerpt }]
  negative_indicators_triggered: [{ indicator, learner_excerpt }]
  overall_score: float (0.0–1.0)
  grounded_feedback: string  (cites the passage, not general knowledge)
```

The `grounded_feedback` field is what the learner sees. It explains what their answer got right or wrong by pointing to specific passage text.

### 4.3 Spaced Repetition Integration

Per-learner, per-concept memory record:

```
ConceptMemoryRecord
  ├── learner_id, concept_id
  ├── stability: float          (estimated memory strength)
  ├── difficulty: float         (empirical difficulty for this learner)
  ├── last_reviewed_at, next_review_at
  └── current_mastery: float
```

Scheduling uses a forgetting-curve model: parameters updated after every review event using score and response time. The spaced repetition queue surfaces as a **review bar** before each session: "You have 3 concepts due for review. Review now or continue?"

### 4.4 Mastery Thresholds and Progression Gates

A learner cannot advance to the next module until their module mastery score >= the mastery threshold — unless the instructor has set a `soft` gate (warning, not block) or the learner has exceeded a `gate_override_after_days` safety valve.

When a learner hits a gate: the system identifies struggling concepts, surfaces targeted review items, and offers supplementary passages from the corpus relevant to detected misconceptions. It does not generate new content outside the corpus.

---

## 5. Cohort and Social Learning

### 5.1 Shared Corpus, Individual Progress Tracks

All students in a cohort read from the same published corpus. What is personalized: progress state, mastery scores, spaced repetition schedules, and annotation visibility.

This shared-corpus model is deliberate: social learning features (discussion, peer annotation) only function coherently when everyone is reading the same text.

### 5.2 Passage-Anchored Discussion Threads

Discussion threads are attached to **source passages**, not lesson pages. Every thread carries a `passage_id` and displays the passage excerpt as its header.

Floating discussion — posts not anchored to any source — is not supported. This is a deliberate epistemic forcing function: it requires learners to engage with source material to formulate their question, and keeps discussions locatable over time.

```
DiscussionThread
  ├── id: uuid
  ├── passage_id: uuid           (always a source passage)
  ├── learning_path_id, cohort_id
  └── posts: DiscussionPost[]

DiscussionPost
  ├── body: string
  ├── passage_quote: string | null
  └── inline_citations: PassageCitation[]
```

### 5.3 Peer Annotation

Learners can highlight spans within source passages and attach notes. Private by default; instructors can enable shared annotation visibility.

```
PassageAnnotation
  ├── passage_id, annotator_id
  ├── span_start, span_end     (character offsets)
  ├── note: string | null
  └── visibility: private | cohort | public
```

Annotations are a layer rendered on top of an immutable passage — they never modify source text. Annotation density maps show instructors which spans are most frequently highlighted across the cohort — a signal for both importance and difficulty.

### 5.4 Instructor Analytics: Comprehension Heatmaps and Misconception Detection

Per concept:
- Mastery distribution histogram
- Average attempts before mastery
- Common wrong answers (with misconception labels)
- Open-ended negative indicators triggered across cohort
- Passage engagement: which source passages are being opened

After a threshold number of learners attempt a concept's assessments, the system surfaces a **misconception report** including `suggested_corpus_additions` — passages in the corpus not currently linked to the concept but semantically relevant to the detected misconceptions.

---

## 6. AI Curriculum Agent Design

### 6.1 Inputs to the Agent

```
CurriculumAgentInput
  ├── corpus: CorpusSnapshot
  ├── learning_goal: string
  ├── time_budget_hours: float
  ├── prior_knowledge_signals: PriorKnowledgeSignal[]
  ├── audience_profile: { technical_level, domain_familiarity, register }
  ├── existing_path: LearningPath | null   (if present: regenerate, not fresh)
  └── instructor_constraints: InstructorConstraint[]
```

### 6.2 How the Agent Proposes a Sequence

**Step 1 — Concept extraction.** Embed all corpus passages, run semantic clustering. Discard clusters with fewer than 2 passages (corpus covers them too thinly to support reliable assessment).

**Step 2 — Prerequisite detection.** For each concept pair (A, B), determine: "Does understanding B require terminology or ideas introduced in A?" Output: a directed edge with `strength` (required/recommended) and `rationale`.

```
PREREQUISITE CHECK PROMPT (pseudocode):
  SYSTEM: You are reasoning about learning dependencies.
  INPUT: concept_a: { title, passage_texts }, concept_b: { title, passage_texts }
  QUESTION: Does a learner need to understand concept_a before concept_b,
            based solely on these passages?
  OUTPUT: { depends: boolean, strength: required | recommended, rationale: string }
```

**Step 3 — Pacing and sequencing.** Topologically sort the concept DAG. Apply pacing heuristics: max 3 concepts per lesson, group concepts with high mutual prerequisite density into the same module, fit to time budget by marking low-priority concepts `optional`.

**Step 4 — Explanation and assessment generation.** Parallel per-concept generation once the prerequisite graph is stable.

### 6.3 Iteration: Learner Feedback Reshaping the Path

After a learner has progressed through at least one module, the agent can accept a **path refinement request** — inputs include mastery scores, learner's stated feedback, and assessment item response patterns. The agent produces a **path delta** (not a full regeneration) reviewed by the instructor before being applied.

### 6.4 What the Agent Cannot Do — Explicit Scope Limits

1. **Cannot generate content absent from the corpus.** If a concept requires knowledge not in any passage, the agent omits it or flags it as insufficiently grounded.
2. **Cannot create assessment items without a grounding passage.**
3. **Cannot infer prerequisites not derivable from the corpus.** It can only detect dependencies visible in how passages reference each other.
4. **Cannot grade subjective quality.** Open-ended verification checks consistency with source material, not writing quality or analytical depth.
5. **Cannot suppress or override instructor annotations.** Instructor annotations that render instead of AI-generated explanations always take precedence.

---

## 7. Integration with the Knowledge Core

### 7.1 How the Learning Layer Calls the RAG Layer

The learning layer never accesses source documents directly. It always calls the Knowledge Core's retrieval API. Key call patterns:

**Concept extraction (corpus scan):**
```
POST /core/passages/semantic-cluster
{ corpus_id, min_cluster_size: 2, granularity: "concept" }
→ [{ cluster_id, passages: PassageCitation[], centroid_embedding }]
```

**Explanation generation (retrieval-augmented):**
```
POST /core/passages/retrieve
{ corpus_id, query: "write-ahead logging crash recovery", top_k: 5, rerank: true }
→ [{ passage_id, text, score, document_title, section_label }]
```
Retrieved passages are passed to the generation model as context. The model cites from this context — it is not given the full corpus in the generation prompt.

All retrieval calls include a `corpus_snapshot_version` parameter. Responses include a passage version hash stored in every `PassageCitation` record, enabling staleness detection.

### 7.2 Corpus Change Propagation

When a source is added, edited, or deleted, the Knowledge Core emits a `CorpusChangeEvent`. The learning layer subscribes and runs a **staleness check**:

1. For each `PassageCitation` pointing to an affected passage, compare version hashes
2. If hashes differ: mark the citing concept as `citation_status: stale`
3. Aggregate stale concepts into a **path health report** for the path owner

**Staleness does not invalidate the learner experience** — it is a signal to the path owner, not a gate on the learner. Only `passage_deleted` events where a concept's sole supporting passage is removed trigger a harder `grounding_broken` status.

### 7.3 Version Control for Learning Paths

Learning path versions increment when an instructor publishes a revision, the agent generates a new proposal, or a path delta is applied.

**Version migration policy:**
- **Additive changes** (new concept in a module the learner hasn't reached): unaffected
- **Non-structural changes** (explanation regenerated): learner sees updated explanation; mastery score preserved
- **Structural changes** (reorder that moves content before a completed lesson): system calculates impact; instructor chooses migration option
- **Grounding changes** (a passage a learner answered questions about has been edited): mastery scores flagged; learner offered optional re-review, but score not automatically reset

---

## 8. MVP vs Full Build

### 8.1 The Smallest Version That Demonstrates the Core Value

**Must be in MVP:**
1. A corpus (even a single document) processed into passages
2. The Curriculum Agent generating a path proposal: at minimum a flat sequence of concepts with explanations and citations (no prerequisite graph)
3. Each concept explanation carrying visible inline citations linkable to the source passage
4. At least one MC assessment item per concept with a grounding passage and distractor rationale
5. The ability for a human to review the proposal, accept or override individual concepts, and publish
6. A learner-facing reading and assessment experience with grounded feedback on wrong answers

### 8.2 MVP Scope Table

| Capability | MVP | Full Build | Notes |
|---|---|---|---|
| Single-document corpus ingestion | YES | YES | |
| Multi-document corpus | NO | YES | Requires cross-document passage resolution |
| AI concept extraction and path proposal | YES | YES | Core thesis requirement |
| Prerequisite graph inference | NO | YES | MVP uses flat linear sequence |
| Instructor review and override interface | YES | YES | Core thesis requirement |
| Grounded concept explanations with citations | YES | YES | Core thesis requirement |
| MC assessment with grounded feedback | YES | YES | Core thesis requirement |
| Open-ended assessment with rubric | NO | YES | Requires OE verification pipeline |
| Source retrieval question type | NO | YES | |
| Spaced repetition scheduling | NO (simplified) | YES | MVP: simple fixed intervals |
| Mastery thresholds and progression gates | NO (soft) | YES | MVP surfaces score without blocking |
| Cohort enrollment and shared progress | NO | YES | MVP is single-learner |
| Passage-anchored discussion | NO | YES | Requires cohort |
| Comprehension heatmaps | NO | YES | Requires cohort analytics |
| Corpus change events and staleness detection | NO | YES | Requires event infrastructure |
| Learning path versioning and migration | NO | YES | Single version at MVP |
| Mid-stream path refinement from learner feedback | NO | YES | |

### 8.3 What Requires the Full AI Core vs Simpler Mechanics

**Requires full Knowledge Core (cannot substitute simpler mechanics):**
- Concept extraction from large multi-document corpus
- Retrieval-augmented explanation generation with bounded citation surface
- Open-ended answer verification against corpus passages
- Misconception-driven supplementary passage retrieval

**Can ship at MVP with simpler mechanics:**
- **Concept extraction from a single document**: chunking + title-based heuristics rather than semantic clustering
- **Assessment generation**: generate-from-passage prompt without retrieval (passage is already known)
- **Citation linking**: document + section label without deep passage-level anchor infrastructure
- **Spaced repetition**: fixed interval doubling (1d, 3d, 7d, 14d) rather than a full forgetting-curve model

The key MVP constraint: every MVP mechanic must be upgradable to the full mechanic without schema migrations that break learner progress records. The data model defined above is designed for the full build; the MVP implements a subset of it, not a different model.
