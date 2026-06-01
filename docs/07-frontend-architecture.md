# Frontend Architecture — Knowledge Commons

**Stack:** Vue 3 + Nuxt 3 + Tailwind CSS + Pinia  
**Version:** 0.1

---

## 1. Stack Decisions

### Vue 3 + Nuxt 3

Nuxt 3's hybrid rendering is the right fit for this product's two distinct surface types:

- **Public collection boards** need SSR — curators want their boards discoverable by search engines and shareable as rich previews. Fast initial paint matters; the content is the product.
- **Knowledge base Q&A, learning paths, and the curation workspace** are full SPA — no SEO value, high interactivity, real-time state (streaming AI responses, WebSocket presence, ingestion progress).

Nuxt 3's `routeRules` handles both from one codebase:

```ts
// nuxt.config.ts
export default defineNuxtConfig({
  routeRules: {
    '/explore/**': { ssr: true },          // public boards — rendered server-side
    '/u/**': { ssr: true },                // public curator profiles
    '/kb/**': { ssr: false },              // knowledge base workspace — SPA
    '/learn/**': { ssr: false },           // learning paths — SPA
    '/board/**': { ssr: false },           // curation workspace — SPA
  }
})
```

**Why not React/Next.js:** Vue 3's reactivity model (fine-grained `ref`/`computed`) maps more cleanly onto the platform's real-time patterns — streaming token output, WebSocket presence, ingestion progress — without the ceremony of `useEffect` dependency arrays.

### Tailwind CSS

Tailwind is chosen over SCSS/BEM for AI interpretability and codebase navigability:

- **Co-location:** Style and structure live in the same file per component. An AI (or a developer) reading a component sees the complete visual specification without cross-referencing a stylesheet.
- **No cascade to model:** Atomic utilities have no specificity interactions. What's in the template is what renders — no inherited rules, no global overrides to trace.
- **Component names carry the semantic layer:** `.knowledge-base__card--active` would carry semantic meaning in BEM, but in a component architecture that meaning lives at the component level (`<SourceCard :active />`) — enforced by the framework, not by naming convention.
- **No dead CSS:** If a utility class isn't in a template, it isn't in the build output.

**Exceptions:** Raw SCSS is used for two things Tailwind handles awkwardly:
1. Complex keyframe animations (ingestion progress pulse, streaming text cursor)
2. The free-form canvas layer (Konva.js integration, custom cursor states, pointer-event management)

These live in `assets/styles/animations.scss` and `assets/styles/canvas.scss` — isolated, not a BEM system.

### Pinia

Official Vue state management. Replaces Vuex. Stores are typed, modular, and composable. Key stores:

- `useKnowledgeBaseStore` — active KB, query state, streaming response buffer
- `useIngestionStore` — per-source ingestion job state, WebSocket progress events
- `useBoardStore` — collection board items, layout state, presence
- `useAuthStore` — current user, JWT, permissions

### Additional Libraries

| Library | Purpose | Notes |
|---|---|---|
| VueUse | Composable utilities — WebSocket, IntersectionObserver, localStorage | Zero overhead, tree-shaken |
| Tiptap | Rich text composer for passage annotations and discussion posts | Open source; Vue-native; extensible for custom citation nodes |
| TanStack Query (vue-query) | Server state, caching, background refetching for API calls | Replaces ad-hoc fetch + loading state boilerplate |
| TanStack Table | Headless data tables for comprehension analytics (instructor view) | Framework-agnostic, unstyled — Tailwind-styled via slot |
| Konva.js + vue-konva | Free-form canvas board mode (V2 feature) | Deferred to V2; not in MVP |
| @vueuse/motion | Declarative transition and animation primitives | Replaces most custom CSS animation needs |

---

## 2. Project Structure

```
knowledge-commons-frontend/
├── assets/
│   └── styles/
│       ├── animations.scss    # keyframes only — ingestion pulse, streaming cursor
│       └── canvas.scss        # Konva.js canvas layer styles (V2)
├── components/
│   ├── core/                  # knowledge base layer
│   │   ├── SourceCard.vue
│   │   ├── ChunkCitationPanel.vue
│   │   ├── StreamingResponse.vue
│   │   └── IngestionProgress.vue
│   ├── learning/              # learning layer
│   │   ├── LearningPathNav.vue
│   │   ├── ConceptLesson.vue
│   │   ├── AssessmentItem.vue
│   │   └── SpacedRepetitionBar.vue
│   ├── discovery/             # discovery layer
│   │   ├── CollectionBoard.vue
│   │   ├── BoardSwimLane.vue
│   │   ├── SourceTile.vue
│   │   └── CuratorProfile.vue
│   └── ui/                    # shared primitives
│       ├── Button.vue
│       ├── Modal.vue
│       ├── Tooltip.vue
│       └── ProgressRing.vue
├── composables/
│   ├── useStreamingQuery.ts   # SSE / token streaming from Ollama via BFF
│   ├── useBoardPresence.ts    # WebSocket presence for shared boards
│   └── useIngestionSocket.ts  # WebSocket ingestion progress
├── layouts/
│   ├── default.vue            # authenticated app shell
│   └── public.vue             # SSR-rendered public pages
├── pages/
│   ├── explore/
│   │   └── [boardId].vue      # public board (SSR)
│   ├── u/
│   │   └── [handle].vue       # curator profile (SSR)
│   ├── kb/
│   │   └── [kbId]/
│   │       ├── index.vue      # knowledge base Q&A
│   │       └── sources.vue    # source management
│   ├── learn/
│   │   └── [pathId]/
│   │       └── [moduleId].vue
│   └── board/
│       └── [boardId].vue      # curation workspace
├── stores/
│   ├── knowledgeBase.ts
│   ├── ingestion.ts
│   ├── board.ts
│   └── auth.ts
└── server/                    # Nuxt server routes (the Web BFF layer)
    └── api/
        ├── kb/[id]/query.post.ts     # proxies to backend, handles SSE streaming
        ├── sources/index.post.ts
        └── collections/[id]/fork.post.ts
```

The `server/api/` directory is Nuxt's built-in server routes — these are the Web BFF layer described in `docs/05-platform-architecture.md`. They run server-side, compose calls to the backend services, and handle SSE streaming forwarding to the client. No separate BFF service is needed.

---

## 3. Key Interaction Patterns

### Streaming AI Responses

Ollama's generation API streams tokens via SSE. The flow:

```
Client (StreamingResponse.vue)
  → POST /api/kb/{id}/query          (Nuxt server route)
    → POST http://api:8000/v1/kbs/{id}/query  (backend)
      → Ollama /api/chat (streaming)
    ← SSE token stream forwarded back through Nuxt server route
  ← ReadableStream consumed by useStreamingQuery composable
    → reactive `buffer` ref updated per token → rendered live
```

`useStreamingQuery.ts` exposes `{ response, citations, isStreaming, error }`. The component never sees HTTP directly — it consumes the composable.

### WebSocket Presence

`useBoardPresence.ts` opens a WebSocket to `/api/board/{id}/presence` on mount and closes it on unmount. It maintains a reactive `presentUsers` ref updated by server-sent presence events. The composable handles reconnection with exponential backoff — the component just reads `presentUsers`.

### Citation Side Panel

Clicking any inline citation `[SOURCE:chunk_id]` in a generated response triggers a slide-in panel showing:
- The verbatim passage text (±20 tokens context)
- The source document title and locator (page, timestamp)
- A link to view the full source

The panel is a teleport-rendered overlay so it doesn't break the document flow. The citation is resolved by the frontend against a local map of `{ chunk_id → citation_data }` returned with every generation response — no additional network request on click.

---

## 4. Tailwind Configuration

```ts
// tailwind.config.ts
export default {
  content: [
    './components/**/*.vue',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './composables/**/*.ts',
    './server/**/*.ts',
  ],
  theme: {
    extend: {
      colors: {
        // Semantic tokens — use these in components, not raw palette values
        surface:   { DEFAULT: '#ffffff', secondary: '#f8f7f4' },
        border:    { DEFAULT: '#e5e2db', strong: '#c9c4bc' },
        text:      { primary: '#1a1814', secondary: '#6b6560', muted: '#9b958e' },
        accent:    { DEFAULT: '#2563eb', hover: '#1d4ed8' },
        grounded:  { DEFAULT: '#16a34a', light: '#f0fdf4' }, // citation/grounding indicator
        warning:   { DEFAULT: '#d97706', light: '#fffbeb' }, // low fidelity warning
      },
      fontFamily: {
        sans: ['Inter Variable', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono Variable', 'JetBrains Mono', 'monospace'],
        prose: ['Lora Variable', 'Lora', 'Georgia', 'serif'], // source passage reading
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'stream-cursor': 'stream-cursor 0.8s step-end infinite',
      }
    }
  }
}
```

The `grounded` color token is deliberately named — it appears on citation markers, fidelity indicators, and the "grounded response" badge. It carries the platform's core semantic meaning visually: green = sourced, yellow/orange = uncertain, red = blocked. Consistent use of this token makes grounding state legible at a glance.

---

## 5. MVP vs V2 Frontend Scope

### MVP (ships with the backend MVP)

- Knowledge base Q&A interface with inline citations and side panel
- Ingestion progress (URL paste + PDF upload + WebSocket progress)
- Collection boards in swim-lane mode only
- Fork action with progress state
- Public board view (SSR) with board summary and source cards
- Basic curator profile page
- Learning path reading view with MC assessment and grounded feedback
- Auth: email/password + JWT session

### V2

- Free-form canvas board mode (Konva.js)
- Streaming token animation and cursor
- WebSocket presence indicators on shared boards
- Passage annotation UI (highlight + note)
- Passage-anchored discussion threads
- Comprehension analytics dashboard (instructor view)
- Mobile-optimized card layouts and gesture navigation
- Dark mode (Tailwind `dark:` variants already in config)
