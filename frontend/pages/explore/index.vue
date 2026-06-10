<script setup lang="ts">
definePageMeta({ layout: 'public' })

import { ref, computed } from 'vue'

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

interface HarnessSummary {
  id: string
  title: string
  description: string
  visibility: string
  fork_count: number
  created_at: string
  owner: { id: string; handle: string; display_name: string } | null
  asset_count: number
}

// Active tab
const activeTab = ref<'boards' | 'harnesses'>('boards')

// Boards tab
const { data: trending, pending: trendingPending } = await useFetch<BoardSummary[]>(
  '/api/boards',
  { query: { sort: 'trending', limit: 18 } }
)

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

// Harnesses tab
const harnesses = ref<HarnessSummary[]>([])
const harnessesLoading = ref(false)
const harnessesLoaded = ref(false)

async function loadHarnesses() {
  if (harnessesLoaded.value || harnessesLoading.value) return
  harnessesLoading.value = true
  try {
    // Public harnesses only — no auth header (unauthenticated visitors)
    harnesses.value = await $fetch<HarnessSummary[]>('/api/harnesses', {
      query: { visibility: 'public' },
    }).catch(() => [])
  } finally {
    harnessesLoading.value = false
    harnessesLoaded.value = true
  }
}

function switchTab(tab: 'boards' | 'harnesses') {
  activeTab.value = tab
  if (tab === 'harnesses') loadHarnesses()
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-semibold text-text-primary mb-2">Explore</h1>
      <p class="text-text-secondary">
        Publicly curated knowledge — boards, harnesses, and more.
      </p>
    </div>

    <!-- Tabs -->
    <div class="flex items-center gap-1 mb-8 border-b border-border">
      <button
        class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px"
        :class="activeTab === 'boards'
          ? 'border-accent text-text-primary'
          : 'border-transparent text-text-muted hover:text-text-secondary'"
        @click="switchTab('boards')"
      >
        Boards
      </button>
      <button
        class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px"
        :class="activeTab === 'harnesses'
          ? 'border-accent text-text-primary'
          : 'border-transparent text-text-muted hover:text-text-secondary'"
        @click="switchTab('harnesses')"
      >
        Harnesses
      </button>
    </div>

    <!-- Boards tab -->
    <template v-if="activeTab === 'boards'">
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

      <div v-if="trendingPending && !hasSearched" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <div v-for="n in 6" :key="n" class="rounded-xl border border-border p-5 animate-pulse">
          <div class="h-4 bg-surface-secondary rounded w-3/4 mb-3" />
          <div class="h-3 bg-surface-secondary rounded w-full mb-2" />
          <div class="h-3 bg-surface-secondary rounded w-2/3" />
        </div>
      </div>

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
              <NuxtLink :to="`/u/${board.owner.handle}`" class="hover:text-accent transition-colors" @click.stop>
                @{{ board.owner.handle }}
              </NuxtLink>
            </span>
          </div>
        </NuxtLink>
      </div>

      <div v-else class="text-center py-16 text-text-muted">
        <p class="text-sm">{{ hasSearched ? 'No boards found for that query.' : 'No public boards yet.' }}</p>
      </div>
    </template>

    <!-- Harnesses tab -->
    <template v-if="activeTab === 'harnesses'">
      <div v-if="harnessesLoading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <div v-for="n in 6" :key="n" class="rounded-xl border border-border p-5 animate-pulse">
          <div class="h-4 bg-surface-secondary rounded w-3/4 mb-3" />
          <div class="h-3 bg-surface-secondary rounded w-full mb-2" />
          <div class="h-3 bg-surface-secondary rounded w-2/3" />
        </div>
      </div>

      <div v-else-if="harnesses.length > 0" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <NuxtLink
          v-for="h in harnesses"
          :key="h.id"
          :to="`/harnesses/${h.id}/compose`"
          class="group block rounded-xl border border-border bg-surface p-5 hover:border-accent/40 hover:shadow-sm transition-all"
        >
          <div class="flex items-start justify-between gap-2 mb-3">
            <h2 class="text-sm font-semibold text-text-primary group-hover:text-accent transition-colors line-clamp-2">
              {{ h.title }}
            </h2>
            <span class="shrink-0 text-xs text-text-muted">{{ h.fork_count }} forks</span>
          </div>
          <p v-if="h.description" class="text-xs text-text-secondary leading-5 line-clamp-3 mb-3">
            {{ h.description }}
          </p>
          <div class="flex items-center gap-3 text-xs text-text-muted">
            <span>{{ h.asset_count }} slot{{ h.asset_count !== 1 ? 's' : '' }}</span>
            <span v-if="h.owner">· @{{ h.owner.handle }}</span>
            <span>· {{ formatDate(h.created_at) }}</span>
          </div>
        </NuxtLink>
      </div>

      <div v-else class="text-center py-16 text-text-muted">
        <p class="text-sm">No public harnesses yet.</p>
        <NuxtLink to="/harnesses" class="mt-2 text-sm text-accent hover:underline block">Go to your harnesses</NuxtLink>
      </div>
    </template>
  </div>
</template>
