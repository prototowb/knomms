<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

import { ref, onMounted, onUnmounted } from 'vue'

const route = useRoute()
const auth = useAuthStore()
const boardId = route.params.boardId as string

interface SourceCard {
  id: string; type: string; title: string; ingestion_status: string; raw_url: string | null
}
interface BoardItem {
  id: string; source_id: string; note: string; lane: string; position: number; source: SourceCard | null
}
interface BoardOut {
  id: string; title: string; description: string; visibility: string
  fork_count: number; layout_config: { lanes?: string[] }
  ai_summary: string | null; items: BoardItem[]
}

const board = ref<BoardOut | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Edit mode
const editing = ref(false)
const editTitle = ref('')
const editDesc = ref('')
const editVisibility = ref('private')
const saving = ref(false)

// Add source
const urlInput = ref('')
const noteInput = ref('')
const laneInput = ref('')
const addingUrl = ref(false)
const addUrlError = ref<string | null>(null)
const dragging = ref(false)
const uploading = ref(false)
const uploadError = ref<string | null>(null)

// Lane management
const newLane = ref('')

// Polling for pending source statuses
const pollingIds = ref<Set<string>>(new Set())
let pollTimer: ReturnType<typeof setInterval> | null = null

async function fetchBoard() {
  loading.value = true
  try {
    board.value = await $fetch<BoardOut>(`/api/boards/${boardId}`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    }) as BoardOut
    // Also try to fetch owner's private view (may fail if not owner)
    if (!board.value) throw new Error('Board not found')
    startPollingPending()
  } catch {
    error.value = 'Board not found or not accessible'
  } finally {
    loading.value = false
  }
}

function startPollingPending() {
  if (!board.value) return
  for (const item of board.value.items) {
    const s = item.source
    if (s && s.ingestion_status !== 'embedded' && s.ingestion_status !== 'failed') {
      pollingIds.value.add(s.id)
    }
  }
  if (pollingIds.value.size > 0) startPollTimer()
}

function startPollTimer() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    if (pollingIds.value.size === 0) { clearInterval(pollTimer!); pollTimer = null; return }
    for (const id of [...pollingIds.value]) {
      try {
        const s = await $fetch<SourceCard>(`/api/sources/${id}`, {
          headers: { Authorization: `Bearer ${auth.token}` },
        })
        if (!board.value) return
        for (const item of board.value.items) {
          if (item.source?.id === id) {
            item.source = { ...item.source, ...s }
          }
        }
        if (s.ingestion_status === 'embedded' || s.ingestion_status === 'failed') {
          pollingIds.value.delete(id)
        }
      } catch { pollingIds.value.delete(id) }
    }
  }, 3000)
}

function openEdit() {
  if (!board.value) return
  editTitle.value = board.value.title
  editDesc.value = board.value.description
  editVisibility.value = board.value.visibility
  editing.value = true
}

async function saveEdit() {
  if (saving.value) return
  saving.value = true
  try {
    const updated = await $fetch<BoardOut>(`/api/boards/${boardId}`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { title: editTitle.value, description: editDesc.value, visibility: editVisibility.value },
    })
    if (board.value) {
      board.value.title = updated.title
      board.value.description = updated.description
      board.value.visibility = updated.visibility
    }
    editing.value = false
  } finally {
    saving.value = false
  }
}

async function addLane() {
  const lane = newLane.value.trim()
  if (!lane || !board.value) return
  const lanes = [...(board.value.layout_config.lanes ?? []), lane]
  await $fetch<unknown>(`/api/boards/${boardId}`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${auth.token}` },
    body: { layout_config: { ...board.value.layout_config, lanes } },
  })
  board.value.layout_config.lanes = lanes
  newLane.value = ''
}

async function addSource() {
  const url = urlInput.value.trim()
  if (!url || addingUrl.value) return
  addingUrl.value = true
  addUrlError.value = null
  try {
    const item = await $fetch<BoardItem>(`/api/boards/${boardId}/sources`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { source_url: url, note: noteInput.value.trim(), lane: laneInput.value.trim() },
    })
    board.value?.items.unshift(item)
    urlInput.value = ''
    noteInput.value = ''
    if (item.source?.id) { pollingIds.value.add(item.source.id); startPollTimer() }
  } catch (err: unknown) {
    addUrlError.value = err instanceof Error ? err.message : 'Failed to add source'
  } finally {
    addingUrl.value = false
  }
}

async function uploadFile(file: File) {
  uploading.value = true
  uploadError.value = null
  const form = new FormData()
  form.append('file', file)
  form.append('note', noteInput.value.trim())
  form.append('lane', laneInput.value.trim())
  try {
    const item = await $fetch<BoardItem>(`/api/boards/${boardId}/upload`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: form,
    })
    board.value?.items.unshift(item)
    if (item.source?.id) { pollingIds.value.add(item.source.id); startPollTimer() }
  } catch (err: unknown) {
    uploadError.value = err instanceof Error ? err.message : 'Upload failed'
  } finally {
    uploading.value = false
  }
}

function onDrop(e: DragEvent) {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) uploadFile(file)
}

function onFileInput(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) uploadFile(file)
}

const statusColor: Record<string, string> = {
  embedded: 'text-grounded', pending: 'text-warning', processing: 'text-warning',
  chunked: 'text-accent', failed: 'text-red-500',
}
const typeIcon: Record<string, string> = {
  pdf: '📄', web_page: '🌐', plain_text: '📝', epub: '📚', prompt_asset: '🧩',
}

onMounted(fetchBoard)
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<template>
  <div class="max-w-4xl mx-auto py-8 px-6">
    <div v-if="loading" class="text-text-muted text-sm py-20 text-center animate-pulse">Loading…</div>
    <p v-else-if="error" class="text-warning text-sm py-20 text-center">{{ error }}</p>

    <template v-else-if="board">
      <!-- Header -->
      <div class="flex items-start gap-4 mb-8">
        <div class="flex-1 min-w-0">
          <NuxtLink to="/boards" class="text-xs text-text-muted hover:text-accent flex items-center gap-1 mb-2">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
            My boards
          </NuxtLink>
          <h1 class="text-xl font-semibold text-text-primary">{{ board.title }}</h1>
          <p v-if="board.description" class="text-sm text-text-muted mt-1">{{ board.description }}</p>
          <div class="flex items-center gap-3 mt-2 text-xs text-text-muted">
            <span class="px-2 py-0.5 rounded-full"
              :class="board.visibility === 'public' ? 'text-grounded bg-grounded/10' : 'text-text-muted bg-border'">
              {{ board.visibility }}
            </span>
            <span>{{ board.items.length }} source{{ board.items.length !== 1 ? 's' : '' }}</span>
            <span v-if="board.visibility === 'public'">
              <NuxtLink :to="`/board/${boardId}`" class="text-accent hover:underline">View public page</NuxtLink>
            </span>
          </div>
        </div>
        <button
          class="shrink-0 px-3 py-1.5 rounded-lg text-sm border border-border text-text-secondary hover:bg-surface-secondary transition-colors"
          @click="openEdit"
        >
          Edit
        </button>
      </div>

      <!-- Edit modal -->
      <div
        v-if="editing"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
        @click.self="editing = false"
      >
        <div class="bg-surface rounded-2xl shadow-xl p-6 w-full max-w-md mx-4 space-y-4">
          <h2 class="text-base font-semibold text-text-primary">Edit board</h2>
          <input v-model="editTitle" type="text" placeholder="Title"
            class="w-full border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-accent" />
          <textarea v-model="editDesc" rows="2" placeholder="Description"
            class="w-full border border-border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-accent resize-none" />
          <div class="flex gap-4">
            <label v-for="v in ['private', 'public']" :key="v" class="flex items-center gap-2 cursor-pointer">
              <input type="radio" :value="v" v-model="editVisibility" class="accent-accent" />
              <span class="text-sm text-text-secondary capitalize">{{ v }}</span>
            </label>
          </div>
          <div class="flex gap-3 justify-end">
            <button class="px-4 py-2 text-sm text-text-muted hover:bg-surface-secondary rounded-lg" @click="editing = false">Cancel</button>
            <button :disabled="saving" class="px-4 py-2 text-sm font-medium bg-accent text-white rounded-lg disabled:opacity-50" @click="saveEdit">
              {{ saving ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Left: add sources + lane management -->
        <div class="lg:col-span-1 space-y-6">
          <!-- Add URL -->
          <div class="rounded-xl border border-border bg-surface p-4 space-y-3">
            <h2 class="text-sm font-semibold text-text-primary">Add source</h2>
            <input v-model="urlInput" type="url" placeholder="https://..."
              class="w-full border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent placeholder:text-text-muted" />
            <input v-model="noteInput" type="text" placeholder="Curator note (optional)"
              class="w-full border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent placeholder:text-text-muted" />
            <select v-model="laneInput" class="w-full border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent text-text-primary bg-surface">
              <option value="">No lane</option>
              <option v-for="lane in (board.layout_config.lanes ?? [])" :key="lane" :value="lane">{{ lane }}</option>
            </select>
            <button :disabled="addingUrl || !urlInput.trim()"
              class="w-full py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
              @click="addSource">
              {{ addingUrl ? 'Adding…' : 'Add URL' }}
            </button>
            <p v-if="addUrlError" class="text-xs text-warning">{{ addUrlError }}</p>

            <!-- File drop -->
            <label class="block rounded-lg border-2 border-dashed p-4 text-center cursor-pointer transition-colors"
              :class="dragging ? 'border-accent bg-accent/5' : 'border-border hover:border-accent/50'"
              @dragover.prevent="dragging = true" @dragleave="dragging = false" @drop.prevent="onDrop">
              <input type="file" class="sr-only" accept=".pdf,.txt,.md,.docx" :disabled="uploading" @change="onFileInput" />
              <p class="text-xs text-text-muted">{{ uploading ? 'Uploading…' : 'Drop a PDF or text file' }}</p>
            </label>
            <p v-if="uploadError" class="text-xs text-warning">{{ uploadError }}</p>
          </div>

          <!-- Lane management -->
          <div class="rounded-xl border border-border bg-surface p-4 space-y-3">
            <h2 class="text-sm font-semibold text-text-primary">Swim lanes</h2>
            <ul class="space-y-1">
              <li v-for="lane in (board.layout_config.lanes ?? [])" :key="lane"
                class="text-sm text-text-secondary px-2 py-1 rounded bg-surface-secondary">
                {{ lane }}
              </li>
              <li v-if="!(board.layout_config.lanes ?? []).length" class="text-xs text-text-muted">No lanes defined</li>
            </ul>
            <div class="flex gap-2">
              <input v-model="newLane" type="text" placeholder="New lane name"
                class="flex-1 border border-border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-accent placeholder:text-text-muted"
                @keydown.enter="addLane" />
              <button :disabled="!newLane.trim()" class="px-3 py-1.5 rounded-lg text-sm bg-accent text-white hover:bg-accent-hover disabled:opacity-50"
                @click="addLane">+</button>
            </div>
          </div>
        </div>

        <!-- Right: source list -->
        <div class="lg:col-span-2">
          <h2 class="text-sm font-semibold text-text-secondary mb-3">
            Sources
            <span class="font-normal text-text-muted ml-1">({{ board.items.length }})</span>
          </h2>
          <p v-if="board.items.length === 0" class="text-sm text-text-muted">
            No sources yet — add a URL or upload a file.
          </p>
          <ul v-else class="space-y-2">
            <li v-for="item in board.items" :key="item.id"
              class="rounded-lg border border-border bg-surface p-3 flex items-start gap-3">
              <span class="text-base mt-0.5 shrink-0">{{ typeIcon[item.source?.type ?? ''] ?? '📎' }}</span>
              <div class="flex-1 min-w-0">
                <a v-if="item.source?.raw_url" :href="item.source.raw_url" target="_blank" rel="noopener"
                  class="text-sm font-medium text-text-primary hover:text-accent transition-colors line-clamp-1">
                  {{ item.source?.title || item.source?.raw_url }}
                </a>
                <p v-else class="text-sm font-medium text-text-primary line-clamp-1">{{ item.source?.title || 'Untitled' }}</p>
                <p v-if="item.note" class="text-xs text-text-muted mt-0.5 line-clamp-2 border-l-2 border-grounded/30 pl-2">
                  {{ item.note }}
                </p>
                <div class="flex items-center gap-3 mt-1 text-xs">
                  <span :class="statusColor[item.source?.ingestion_status ?? ''] ?? 'text-text-muted'">
                    {{ item.source?.ingestion_status ?? '—' }}
                    <span v-if="item.source && pollingIds.has(item.source.id)"
                      class="ml-1 inline-block w-1 h-1 rounded-full bg-current animate-bounce" />
                  </span>
                  <span v-if="item.lane" class="text-text-muted">{{ item.lane }}</span>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </template>
  </div>
</template>
