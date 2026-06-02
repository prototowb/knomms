<script setup lang="ts">
definePageMeta({ layout: 'public' })

const route = useRoute()
const boardId = route.params.boardId as string
const auth = useAuthStore()

interface SourceCardOut {
  id: string
  type: string
  title: string
  description: string
  raw_url: string | null
  ingestion_status: string
}

interface BoardItemOut {
  id: string
  source_id: string
  note: string
  lane: string
  position: number
  added_at: string
  source: SourceCardOut | null
}

interface CuratorOut {
  id: string
  handle: string
  display_name: string
}

interface BoardOut {
  id: string
  title: string
  description: string
  visibility: string
  fork_count: number
  forked_from_id: string | null
  fork_lineage: string[]
  layout_config: { mode?: string; lanes?: string[] }
  ai_summary: string | null
  item_count: number
  created_at: string
  updated_at: string
  owner: CuratorOut | null
  items: BoardItemOut[]
}

// SSR fetch
const { data: board, error } = await useFetch<BoardOut>(`/api/boards/${boardId}`)

// Fork dialog
const showFork = ref(false)
const forkTitle = ref('')
const forking = ref(false)
const forkError = ref<string | null>(null)

async function forkBoard() {
  if (!forkTitle.value.trim() || forking.value) return
  if (!auth.isLoggedIn) {
    await navigateTo('/login')
    return
  }
  forking.value = true
  forkError.value = null
  try {
    const result = await $fetch<{ id: string }>(`/api/boards/${boardId}/fork`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { new_title: forkTitle.value.trim(), visibility: 'private' },
    })
    showFork.value = false
    await navigateTo(`/kb/${result.id}`)
  } catch (err: unknown) {
    forkError.value = err instanceof Error ? err.message : 'Fork failed'
  } finally {
    forking.value = false
  }
}

// Group items by lane for swim-lane layout
const lanes = computed(() => {
  if (!board.value) return []
  const config = board.value.layout_config
  const definedLanes: string[] = config.lanes ?? []

  // Collect all lane names including ones from items not in defined lanes
  const allLanes = new Set<string>(definedLanes)
  for (const item of board.value.items) {
    if (item.lane) allLanes.add(item.lane)
  }
  if (!allLanes.size) allLanes.add('Sources')

  return Array.from(allLanes).map(lane => ({
    label: lane,
    items: board.value!.items.filter(i => (i.lane || 'Sources') === lane),
  })).filter(l => l.items.length > 0)
})

const sourceTypeIcon: Record<string, string> = {
  pdf: '📄',
  web_page: '🌐',
  video: '🎬',
  audio: '🎵',
  plain_text: '📝',
  epub: '📚',
}

// Init fork title from board title
watch(showFork, (v) => {
  if (v && board.value) forkTitle.value = `${board.value.title} [fork]`
})

// AI summary generation
const summarizing = ref(false)
const summaryError = ref<string | null>(null)

const isOwner = computed(() =>
  auth.isLoggedIn && board.value?.owner?.handle === auth.user?.handle
)

async function generateSummary() {
  if (summarizing.value) return
  summarizing.value = true
  summaryError.value = null
  try {
    const result = await $fetch<{ summary: string }>(`/api/boards/${boardId}/generate-summary`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    if (board.value) board.value = { ...board.value, ai_summary: result.summary }
  } catch (err: unknown) {
    summaryError.value = err instanceof Error ? err.message : 'Summary generation failed'
  } finally {
    summarizing.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-surface">
    <div v-if="error" class="text-center py-20 text-warning text-sm">Board not found or not public.</div>

    <template v-else-if="board">
      <!-- Board header -->
      <div class="border-b border-border bg-surface">
        <div class="max-w-6xl mx-auto px-6 py-8">
          <div class="flex items-start gap-6">
            <div class="flex-1 min-w-0">
              <p v-if="board.owner" class="text-xs text-text-muted mb-2">
                Curated by
                <NuxtLink :to="`/u/${board.owner.handle}`" class="text-accent hover:underline">
                  @{{ board.owner.handle }}
                </NuxtLink>
              </p>
              <h1 class="text-2xl font-semibold text-text-primary mb-2">{{ board.title }}</h1>
              <p v-if="board.ai_summary" class="text-sm text-text-secondary leading-6 max-w-2xl">
                {{ board.ai_summary }}
              </p>
              <p v-else-if="board.description" class="text-sm text-text-secondary leading-6 max-w-2xl">
                {{ board.description }}
              </p>

              <ClientOnly>
                <div v-if="isOwner" class="mt-3 flex items-center gap-3">
                  <button
                    :disabled="summarizing"
                    class="text-xs px-3 py-1.5 rounded-lg border border-border text-text-muted hover:bg-surface-secondary disabled:opacity-50 transition-colors"
                    @click="generateSummary"
                  >
                    {{ summarizing ? 'Generating summary…' : board.ai_summary ? 'Regenerate summary' : 'Generate AI summary' }}
                  </button>
                  <p v-if="summaryError" class="text-xs text-warning">{{ summaryError }}</p>
                </div>
              </ClientOnly>

              <div class="flex items-center gap-4 mt-3 text-xs text-text-muted">
                <span>{{ board.items.length }} source{{ board.items.length !== 1 ? 's' : '' }}</span>
                <span>{{ board.fork_count }} fork{{ board.fork_count !== 1 ? 's' : '' }}</span>
                <span v-if="board.forked_from_id">
                  Forked from
                  <NuxtLink :to="`/board/${board.forked_from_id}`" class="text-accent hover:underline">
                    original board
                  </NuxtLink>
                </span>
              </div>
            </div>

            <!-- Fork button -->
            <button
              class="shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover transition-colors"
              @click="showFork = true"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
              Fork this board
            </button>
          </div>
        </div>
      </div>

      <!-- Fork dialog -->
      <div
        v-if="showFork"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
        @click.self="showFork = false"
      >
        <div class="bg-surface rounded-2xl shadow-xl p-6 w-full max-w-md mx-4">
          <h2 class="text-base font-semibold text-text-primary mb-1">Fork this board</h2>
          <p class="text-xs text-text-muted mb-4">
            Creates a private copy with all {{ board.items.length }} sources queued for indexing.
            You&#x27;ll be able to query it in a few minutes.
          </p>
          <input
            v-model="forkTitle"
            type="text"
            placeholder="Name for your fork"
            class="w-full border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent mb-3"
            @keydown.enter="forkBoard"
          />
          <p v-if="forkError" class="text-xs text-warning mb-3">{{ forkError }}</p>
          <div class="flex gap-3 justify-end">
            <button
              class="px-4 py-2 rounded-lg text-sm text-text-muted hover:bg-surface-secondary transition-colors"
              @click="showFork = false"
            >
              Cancel
            </button>
            <button
              :disabled="!forkTitle.trim() || forking"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
              @click="forkBoard"
            >
              {{ forking ? 'Forking…' : 'Fork' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Swim-lane content -->
      <div class="max-w-6xl mx-auto px-6 py-8">
        <div v-if="lanes.length === 0" class="text-center py-16 text-text-muted text-sm">
          This board has no sources yet.
        </div>
        <div v-else class="space-y-10">
          <section v-for="lane in lanes" :key="lane.label">
            <h2 class="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-4">
              {{ lane.label }}
              <span class="ml-2 font-normal normal-case text-text-muted">{{ lane.items.length }}</span>
            </h2>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              <div
                v-for="item in lane.items"
                :key="item.id"
                class="rounded-xl border border-border bg-surface p-4 flex flex-col gap-2"
              >
                <!-- Type badge -->
                <div class="flex items-center gap-2">
                  <span class="text-base" :title="item.source?.type">
                    {{ sourceTypeIcon[item.source?.type ?? ''] ?? '📎' }}
                  </span>
                  <span class="text-xs text-text-muted font-mono truncate flex-1">
                    {{ item.source?.type?.replace('_', ' ') ?? 'source' }}
                  </span>
                  <span
                    v-if="item.source?.ingestion_status === 'embedded'"
                    class="text-xs text-grounded"
                    title="Indexed"
                  >●</span>
                  <span
                    v-else-if="item.source?.ingestion_status !== 'embedded'"
                    class="text-xs text-warning"
                    title="Indexing…"
                  >○</span>
                </div>

                <!-- Title -->
                <a
                  v-if="item.source?.raw_url"
                  :href="item.source.raw_url"
                  target="_blank"
                  rel="noopener"
                  class="text-sm font-medium text-text-primary hover:text-accent transition-colors line-clamp-2"
                >
                  {{ item.source?.title || item.source?.raw_url }}
                </a>
                <p v-else class="text-sm font-medium text-text-primary line-clamp-2">
                  {{ item.source?.title || 'Untitled' }}
                </p>

                <!-- Curator note -->
                <p v-if="item.note" class="text-xs text-text-secondary leading-5 line-clamp-3 border-l-2 border-grounded/30 pl-2">
                  {{ item.note }}
                </p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>
