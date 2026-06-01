<script setup lang="ts">
definePageMeta({ layout: 'public' })

interface CuratorOut {
  id: string
  handle: string
  display_name: string
}

interface BoardSummary {
  id: string
  title: string
  description: string
  visibility: string
  fork_count: number
  item_count: number
  ai_summary: string | null
  created_at: string
  owner: CuratorOut | null
}

// SSR data fetch — trending boards
const { data: trending, pending: trendingPending } = await useFetch<BoardSummary[]>(
  '/api/boards',
  { query: { sort: 'trending', limit: 18 } }
)

// Client-side search state
const searchQuery = ref('')
const searchResults = ref<BoardSummary[]>([])
const searching = ref(false)
const hasSearched = ref(false)

async function runSearch() {
  const q = searchQuery.value.trim()
  if (!q || searching.value) return
  searching.value = true
  hasSearched.value = true
  try {
    const results = await $fetch<BoardSummary[]>('/api/boards/search', { query: { q } })
    searchResults.value = results
  } finally {
    searching.value = false
  }
}

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = []
  hasSearched.value = false
}

const displayBoards = computed(() =>
  hasSearched.value ? searchResults.value : (trending.value ?? [])
)
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <!-- Header -->
    <div class="mb-10">
      <h1 class="text-3xl font-semibold text-text-primary mb-2">Explore Knowledge Boards</h1>
      <p class="text-text-secondary">
        Publicly curated collections — each a seeded knowledge base you can fork and query.
      </p>
    </div>

    <!-- Search -->
    <div class="mb-8 flex gap-3 max-w-xl">
      <div class="relative flex-1">
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Search by topic, e.g. &#x27;urban heat islands&#x27;"
          class="w-full border border-border rounded-lg px-4 py-2.5 pr-10 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
          @keydown.enter="runSearch"
        />
        <button
          v-if="searchQuery"
          class="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
          aria-label="Clear search"
          @click="clearSearch"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <button
        :disabled="!searchQuery.trim() || searching"
        class="px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
        @click="runSearch"
      >
        {{ searching ? 'Searching…' : 'Search' }}
      </button>
    </div>

    <p class="text-xs text-text-muted mb-6">
      <span v-if="hasSearched">
        {{ searchResults.length }} result{{ searchResults.length !== 1 ? 's' : '' }} for
        &#x22;{{ searchQuery }}&#x22; —
        <button class="text-accent hover:underline" @click="clearSearch">show trending</button>
      </span>
      <span v-else>Trending — boards ranked by forks</span>
    </p>

    <!-- Loading skeleton -->
    <div v-if="trendingPending && !hasSearched" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      <div v-for="n in 6" :key="n" class="rounded-xl border border-border p-5 animate-pulse">
        <div class="h-4 bg-surface-secondary rounded w-3/4 mb-3" />
        <div class="h-3 bg-surface-secondary rounded w-full mb-2" />
        <div class="h-3 bg-surface-secondary rounded w-2/3" />
      </div>
    </div>

    <!-- Board grid -->
    <div v-else-if="displayBoards.length > 0" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      <NuxtLink
        v-for="board in displayBoards"
        :key="board.id"
        :to="`/board/${board.id}`"
        class="group block rounded-xl border border-border bg-surface p-5 hover:border-accent/40 hover:shadow-sm transition-all"
      >
        <div class="flex items-start justify-between gap-2 mb-3">
          <h2 class="text-sm font-semibold text-text-primary group-hover:text-accent transition-colors line-clamp-2">
            {{ board.title }}
          </h2>
          <span class="shrink-0 text-xs text-text-muted">{{ board.fork_count }} forks</span>
        </div>

        <p v-if="board.ai_summary" class="text-xs text-text-secondary leading-5 line-clamp-3 mb-3">
          {{ board.ai_summary }}
        </p>
        <p v-else-if="board.description" class="text-xs text-text-secondary leading-5 line-clamp-3 mb-3">
          {{ board.description }}
        </p>

        <div class="flex items-center gap-3 text-xs text-text-muted mt-auto">
          <span>{{ board.item_count }} source{{ board.item_count !== 1 ? 's' : '' }}</span>
          <span v-if="board.owner">·</span>
          <span v-if="board.owner">
            <NuxtLink
              :to="`/u/${board.owner.handle}`"
              class="hover:text-accent transition-colors"
              @click.stop
            >
              @{{ board.owner.handle }}
            </NuxtLink>
          </span>
        </div>
      </NuxtLink>
    </div>

    <div v-else class="text-center py-16 text-text-muted">
      <p class="text-sm">{{ hasSearched ? 'No boards found for that query.' : 'No public boards yet.' }}</p>
    </div>
  </div>
</template>
