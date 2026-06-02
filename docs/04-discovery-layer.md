# Knowledge Comms — Layer 3: Discovery and Curation Layer

## Product Specification v0.1

---

## 1. Core Concept: Curation as Knowledge Seeding

### What a Collection Board Is

A collection board is a visually browsable, spatially organized set of sources. Each item on the board is not a shortcut or a reference link — it is a source record that the platform's knowledge core can ingest, chunk, embed, and reason over.

A single board might contain: four PDF papers on urban heat islands, a long-read article about green roofing regulation, a government dataset of surface temperature measurements, a documentary transcript, and three video transcripts on passive cooling techniques. Together, these are not a reading list. They are a corpus.

### How Curation Differs from Bookmarking

Bookmarking is a personal archival act. Curation in Knowledge Comms is a semantic act: the curator asserts that these sources, taken together, constitute a meaningful knowledge domain.

- Every item added to a board triggers metadata extraction and source validation at the ingestion layer
- The platform can already begin producing a structured overview of the board's coverage — gaps, thematic clusters, tone diversity — even before a fork
- A public board is implicitly a claim: "this set of sources, combined, is a useful starting point for understanding X"

The discipline of curation (selecting, grouping, annotating) transforms a collection of links into a knowledge seed.

### The Fork/Remix Mechanic

Forking is the central interaction that bridges the Discovery Layer with the Knowledge Core.

**User flow:**

```
1. User browses: "Agroecology in the Global South"
   — 12 source cards in 3 clusters: "Soil biology", "Land tenure policy",
     "Regenerative practice case studies"

2. User clicks "Fork this board"

3. Platform prompts:
   — New KB name (pre-filled: "Agroecology in the Global South [fork]")
   — Visibility (default: private)
   — Option to include/exclude individual cards

4. System creates KB, copies sources, queues ingestion:
   — Sources in shared ingestion cache: ready immediately
   — New sources: ~4 min to index
   — Progress state: "Building your knowledge base — 8 of 12 sources indexed"

5. Once complete, AI core activates:
   — User can query, synthesize, and cite
   — Fork lineage recorded with attribution to original curator
```

A fork is a living copy, not a static snapshot. The original board is unaffected.

### Attribution and Remix Lineage

Every forked knowledge base carries a visible attribution record:

```
This knowledge base was seeded from:
  "Agroecology in the Global South"
  Curated by @dr.okonkwo — Published March 2026

  Also incorporates sources from:
  "Land Reform Policy in Sub-Saharan Africa" — curated by @soillab_collective
  (3 sources from this board merged in on April 2026)
```

Multi-level lineage chains are displayed as a collapsible tree. Curators whose boards are widely forked earn a visible contribution signal on their profile independent of follower counts.

---

## 2. Visual Interface Design Principles

### Board-Style Spatial Layout

Two modes, toggleable per board:

**Swim-lane mode:** Labeled horizontal or vertical sections defined by the curator (e.g., "Primary literature", "Policy background", "Dissenting views"). Cards slot into sections. Easier to navigate for first-time visitors.

**Free-form canvas mode:** Cards at arbitrary positions on a pannable canvas. Curators form visual clusters, annotate with free-text sticky notes. Viewers pan and zoom. Rewards boards with intrinsic spatial structure (timelines, conceptual maps).

Both modes are fully readable on mobile (scroll/swipe instead of pan/zoom).

### Rich Media Cards

Card anatomy:

```
┌────────────────────────────────────┐
│ [THUMBNAIL or FAVICON + DOMAIN]    │
│                                    │
│  Title of the source               │
│  Author · Publication · Date       │
│                                    │
│  [1–2 line excerpt or description] │
│                                    │
│  [Tag: soil biology] [Tag: policy] │
│  [PDF · 28pp]                      │
└────────────────────────────────────┘
```

| Source type | Thumbnail treatment |
|---|---|
| Web article | Open Graph image or favicon strip |
| PDF document | First-page render or cover page extract |
| Video | Thumbnail + duration badge |
| Audio | Waveform illustration + duration |
| Image | Image itself, scaled |
| Dataset | Schema preview (column names, row count) |
| Transcript | Show artwork or speaker avatar |

### Visual Grouping Within a Board

Curators can:
- **Tag cards** with color-coded concept labels (AI-suggested, manually adjustable)
- **Cluster cards** spatially (canvas) or by swim lane
- **Add curator notes**: short text explaining why a source is here, what it adds, or its limitations. These notes travel with the source into forks.

Curator notes are distinct from AI-generated summaries; both may appear on a card in visually distinct styles. The curator's voice is privileged.

### Mobile-First Considerations

- Free-form canvas collapses to vertical scrolling card list on small screens
- Swim-lane mode presented as horizontal swipe-through sections
- Card thumbnails preserved; metadata collapsed behind a tap
- "Add source" always visible as a floating action button
- Mobile capture (photo → OCR → source card) is a first-class entry point

---

## 3. Discovery Mechanics

### AI-Powered Semantic Recommendations

The serendipity engine operates on semantic proximity, not behavioral similarity. It does not use "other users who saved board X also saved board Y."

**How it works:**

1. Retrieve the embedding centroid of the user's current corpus
2. Run nearest-neighbor search against the embedding index of all public boards
3. Rank by cosine similarity, filtered by a minimum quality score
4. Return ranked semantically adjacent boards with dominant thematic overlap labeled

**Example recommendation output:**

```
Because your knowledge base "Urban Climate Resilience" covers:
  — heat island effects, urban greening, surface albedo, policy frameworks

You might find these collections useful:

  "Green Infrastructure Finance Models" — @climate_infra_lab
  Semantic overlap: urban policy, infrastructure funding, municipal governance
  12 sources · forked 34 times

  "Biophilic Design in Dense Cities" — @arch_research_collective
  Semantic overlap: urban vegetation, thermal comfort, built environment
  9 sources · forked 12 times
```

Recommendations are surfaced on the Discovery feed, on any active knowledge base sidebar, and in the post-fork flow ("More boards like this one"). Re-scored every 24 hours as the corpus grows.

### Trending and Popular Collections

Trending is ranked by:
- **Fork-to-active-use ratio** (forks that show continued additions, not abandoned)
- **Curator annotation density** (boards with substantive notes on most cards)
- **Source diversity** (multiple types, multiple publication domains)
- **Recency** of source material in fast-moving domains
- **Human moderation uplift** (positively reviewed by curatorial team)

Pure engagement (views, anonymous traffic) is deliberately excluded. A board with 200 views and 40 active forks ranks above one with 2,000 views and 3 abandoned forks.

### Curator Following

Asymmetric follow. Following surfaces:
- Newly published boards from that curator
- Updates to existing boards (new sources added, annotations revised)
- When a curator forks and publishes an augmented version of someone else's board

Following is oriented around knowledge production, not lifestyle or identity.

### Cross-Collection Search

Query: "indigenous land stewardship and climate resilience"

Results include:
- Public boards with overall topic embedding close to the query
- Individual source cards from any public board matching the query
- Curator profiles whose published corpus matches

Results include an AI-generated explanation of why each result matches: "This board's sources focus on traditional ecological knowledge in Pacific island communities, which has strong thematic overlap with your query."

---

## 4. Community and Social Dynamics

### Curator Profiles

A profile displays: published public boards (by most-forked), inferred expertise signals, lineage (boards they've forked), follower/following counts.

**Expertise signals are inferred, not self-reported:**

```
Inferred expertise areas for @dr.okonkwo:

  Soil ecology           ████████████  High confidence
  Agroecology systems    ███████████   High confidence
  Sub-Saharan land policy ████████     Medium confidence

  Based on: 4 published boards, 47 curated sources,
  citation patterns, and disciplinary spread of indexed material.
  [This is inferred, not verified — see methodology]
```

Curators cannot edit expertise signals directly. They earn and lose them by what they build.

### Collection Visibility Settings

| State | Description |
|---|---|
| **Private** | Owner only. Not indexed for recommendations. |
| **Team-shared** | Visible to org members. Forkable within the team. |
| **Public, read-only** | Visible to all. Cannot be forked. |
| **Public, forkable** | Full visibility. Forkable by any authenticated user. Default. |

Changing from forkable to read-only does not invalidate existing forks.

### Social Actions

**Save:** Copies a board or card into private boards. No ingestion triggered. Lightweight curation — "revisit later."

**Fork:** Primary action. Triggers ingestion and AI core activation.

**Follow:** Asymmetric follow of a curator.

**Comment (grounded):** Must be anchored to a specific source card or quoted passage. Free-floating commentary is not permitted. Discussion on this platform is always discourse *about sources*.

### Preventing Low-Quality Content Proliferation

**Quality floor for discoverability:** To appear in recommendations or trending, a board must have: at least 5 sources, at least 2 groups or tags, at least 3 sources with curator annotation, and at least 1 fully indexable source.

**Pre-publication quality check:**

```
Before publishing "Urban Heat Policy":

  ✓  8 sources — minimum met
  ✓  3 thematic groups defined
  ⚠  5 sources have no curator annotation
  ✗  2 sources could not be fully indexed (paywall detected)

  Boards with curator annotations on most cards receive
  higher placement in recommendations.
```

**Moderation affordances:** Any user can flag a board (reason: low quality, misleading description, duplicative, harmful content). Moderators can downrank, require revision, or remove.

---

## 5. Content Types and Ingestion Entry Points

### Entry Points

**Browser extension:** Toolbar button on any web page. One click adds the current page to a selected board. Optionally, highlighted text becomes the card's seed excerpt.

**Paste URL:** Persistent input on any board. Platform fetches metadata, renders a preview card, user confirms.

**Upload file:** Drag-and-drop zone. Accepts PDF, EPUB, DOCX, MP3, MP4, PNG/JPG, plain text.

### Supported Content Types

| Type | Extraction | Notes |
|---|---|---|
| Web article | Article body text | Paywall detection noted |
| PDF | Full text, figures | Page count shown |
| Video | Transcript (auto or uploaded) | Duration + timestamps |
| Audio | Transcript | Speaker labels if available |
| Image | OCR text + caption | Alt text preserved |
| Dataset (CSV/JSON) | Column names, sample rows | Row count shown |
| EPUB | Full text | Chapter structure preserved |
| Presentation | Text from all slides | Slide count shown |
| Code repository | README + code summary | Language badges |
| Transcript (raw) | Full text | Speaker labels preserved |

### Batch Import

- **Bookmark export files**: Platform parses the file, groups by original folder structure, proposes a board layout with each folder as a swim lane
- **Bibliography formats** (BibTeX, RIS, CSV with DOI/URL column): each entry becomes a source card; DOIs trigger automatic metadata lookup and PDF availability check
- **Reading list files**: Plain text, one URL per line, optional comma-separated title override

### Mobile Capture: Photo to Source Card

1. User photographs a printed page, whiteboard, or book page
2. Platform runs OCR on capture
3. Source card generated with extracted text as body
4. User adds: title, author/source name, date
5. Photograph attached as card thumbnail

---

## 6. AI-Powered Curation Assistance

### "Fill Gaps in This Board"

```
Gap analysis for "Degrowth Economics" (11 sources):

  Current coverage:
  ✓ Strong: theoretical frameworks
  ✓ Moderate: European policy critiques
  ✗ Absent: empirical case studies (real-world implementations)
  ✗ Absent: critiques from Global South perspectives
  ✗ Absent: intersection with labor economics

  Source type balance:
  ✓ Academic papers: 7 (64%)
  ✗ Practitioner/policy documents: 1 (9%)
  ✗ Primary data or datasets: 0

  Suggested searches to fill gaps:
  — "degrowth pilot programs municipal scale empirical evaluation"
  — "post-growth economics sub-Saharan Africa critique"
```

The gap analysis is advisory. The AI does not add sources autonomously.

### Auto-Tagging and Categorization

When a source is added, the platform:
1. Computes a source-level embedding
2. Compares against the board corpus and the platform-wide taxonomy
3. Proposes 2–4 concept tags for the card
4. If the board uses swim-lane grouping, proposes the most appropriate lane

Tags already used in the board are preferred, maintaining tag vocabulary consistency.

### Duplicate and Near-Duplicate Detection

- **Exact duplicate**: Same URL or DOI already in this board — blocked
- **Same source, different URL**: Canonical URL matching, DOI deduplication across mirrors and preprint versions
- **Near-duplicate across boards**: Warns but does not block: "This paper appears to overlap significantly with [X] in your other board. Do you want to link the boards instead of duplicating the source?"

### Board Summary Generation

```
Board summary (AI-generated, reflects sources as of April 2026):

  This collection assembles 14 sources covering the thermodynamic and
  policy dimensions of urban heat islands, with particular attention to
  low-income neighborhoods and distributional effects of cooling
  interventions. Sources span peer-reviewed geophysical modeling,
  municipal planning frameworks, and two longitudinal community health
  studies. The collection does not currently cover adaptation strategies
  in tropical or arid climates.
```

The last sentence always identifies a notable gap or limitation. Curators can accept, edit, or write their own summary. The AI summary is archived and shown on request.

---

## 7. Integration with the Knowledge Core

### The Moment a Board Is Forked

```
T+0s     User clicks "Fork this board"
T+0s     New KB record created; sources copied to user's source library
T+1s     Sources already in shared ingestion cache → marked "ready"
          New sources → queued for ingestion
T+2s     UI transitions to new KB view: "Building your knowledge base — 6 of 14 sources ready"
T+varies  Ingestion completes per-source; user can query partial corpus immediately
T+final   All sources complete. "Your knowledge base is ready" notification sent.
```

Sources in the platform's shared ingestion cache (previously indexed by another user) do not re-ingest. The cache is keyed on canonical URL and content hash.

### Shared Boards as Shared Corpora

When a board has team-shared visibility, all team members contribute to a single shared knowledge base:
- Adding a source to the team board triggers ingestion into the team's KB
- Removing marks it for delayed removal from the team KB
- Any team member can query the shared KB
- Annotations and curator notes remain per-author

A team board is the primary mechanism for collaborative knowledge base construction. The act of deciding what belongs in the board IS the act of deciding what the knowledge base should know.

**Example team board state:**

```
Team: "Climate Policy Research Group"
Board: "Paris Agreement Implementation — Q1 2026 Monitoring"
Visibility: Team-shared (read by 8 members, edit by 4)

Recent additions:
  @mwangi  added "IPCC AR7 Chapter 3 — Mitigation Policy" (Apr 18)
  @torres  added "EU Carbon Border Adjustment Mechanism" (Apr 21)
  @lee     added "China NDC Revision Commentary" (Apr 22)

Knowledge base sync status: All 22 sources indexed ✓
```

### Opt-In Sync to Forks

When a public board is updated, fork owners are notified:

```
An update is available for a board you forked:

  "Agroecology in the Global South" — by @dr.okonkwo
  2 new sources added since you forked on March 3, 2026:

    + "Mycorrhizal networks in polyculture systems" (2025, open access)
    + "Land tenure reform — Kenya 2025 legislation text"

  [Sync these sources into my KB]   [Preview before syncing]   [Ignore]
```

Sync is never automatic. Rejected syncs are recorded and revisitable. Accepted additions go through the same ingestion flow as any new source.

---

## 8. MVP vs Full Build

### The One Loop the MVP Must Prove

> A user discovers a public board, understands its scope, forks it, and has an active queryable knowledge base within minutes.

**Must be in MVP:**
- Public board view with swim-lane layout
- Rich media cards with title, author, date, excerpt, type badge
- Fork action with ingestion progress state
- Fork attribution (one level deep)
- URL paste and PDF upload
- AI-generated board summary with gap acknowledgment
- Semantic search across public boards (centroid nearest-neighbor)
- Curator profile (boards published, basic inferred expertise)
- Basic trending (fork-count ranking with quality floor)

**Can be simplified at MVP:**
- Recommendations: weekly re-scoring vs. daily; basic centroid search
- Gap analysis: source-type imbalance only; perspective gap detection post-MVP
- Auto-tagging: coarser taxonomy, fewer tags, no swim-lane suggestion
- Trending: fork-count + quality floor without full weighted scoring

### What Social Features Wait for V2

- Curator following and Discovery feed
- Grounded comments on source cards
- Free-form canvas mode
- Team-shared boards
- Opt-in fork sync notifications
- Mobile capture
- Batch import (bookmark export, bibliography files)
- Human moderation queue
- Near-duplicate detection across boards
- Read-only vs. forkable distinction (MVP: all public boards forkable)
- Multi-level remix lineage tree

### The Launch Invariant

Every recommendation shown must be explainable by semantic overlap with the user's corpus. No recommendation may be based solely on behavioral co-occurrence. This constraint must be enforced architecturally — not as a best-effort design goal — so that the epistemic integrity of the discovery experience is guaranteed from day one.
