<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useStreamingQuery } from '~/composables/useStreamingQuery'

const route = useRoute()
const auth = useAuthStore()
const kbId = route.params.kbId as string

interface KBMeta {
  id: string
  title: string
  index_status: string
  visibility: string
  owner: { id: string; handle: string; display_name: string } | null
}
const kbMeta = ref<KBMeta | null>(null)
async function fetchKBMeta() {
  kbMeta.value = await $fetch<KBMeta>(`/api/kbs/${kbId}`, {
    headers: { Authorization: `Bearer ${auth.token}` },
  }).catch(() => null)
}

const isOwner = computed(() =>
  auth.isLoggedIn && kbMeta.value?.owner?.id === auth.user?.id
)

const visibilityColor: Record<string, string> = {
  private: 'text-text-muted bg-border',
  team: 'text-accent bg-accent/10',
  public: 'text-grounded bg-grounded/10',
}

function visibilityTitle(v: string): string | undefined {
  const parts: string[] = []
  if (v === 'team') {
    parts.push(
      auth.user?.org_name
        ? `Team — visible to ${auth.user.org_name}`
        : 'Team — visible to members of your organisation'
    )
  }
  if (isOwner.value) parts.push('Click to change visibility')
  return parts.join(' · ') || undefined
}

const shareOpen = ref(false)

const updatingVisibility = ref(false)
async function cycleVisibility() {
  if (!isOwner.value || updatingVisibility.value || !kbMeta.value) return
  const order = ['private', 'team', 'public']
  const next = order[(order.indexOf(kbMeta.value.visibility) + 1) % order.length]
  updatingVisibility.value = true
  try {
    const updated = await $fetch<KBMeta>(`/api/kbs/${kbId}`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { visibility: next },
    })
    kbMeta.value = { ...kbMeta.value, visibility: updated.visibility }
  } catch {
    // leave as-is; the badge simply doesn't change
  } finally {
    updatingVisibility.value = false
  }
}

// ── Q&A ──────────────────────────────────────────────────────────────────────

const queryText = ref('')
const { response, citations, isStreaming, error: qaError, submit } = useStreamingQuery(kbId)

const citationList = computed(() =>
  Object.values(citations.value) as Array<{
    chunk_id: string; source_id: string; locator: string; excerpt: string
  }>
)

async function handleSubmit() {
  if (!queryText.value.trim() || isStreaming.value) return
  await submit(queryText.value)
}

function formatResponse(text: string) {
  return text.replace(
    /\[SOURCE:([a-f0-9-]{36})\]/g,
    '<sup class="text-grounded font-mono text-xs">[src]</sup>'
  )
}

// ── Sources ───────────────────────────────────────────────────────────────────

interface SourceOut {
  id: string; type: string; title: string; ingestion_status: string; created_at: string
}

const activeTab = ref<'query' | 'search' | 'sources'>('query')

// ── KB search (KC-051) ──────────────────────────────────────────────────────

interface ChunkSearchResult {
  chunk_id: string
  source_id: string
  source_title: string
  source_type: string
  locator: string
  text: string
  score: number
}

const kbSearchQuery = ref('')
const kbSearchMode = ref<'semantic' | 'keyword'>('semantic')
const kbSearchResults = ref<ChunkSearchResult[]>([])
const kbSearching = ref(false)
const kbSearched = ref(false)
const kbSearchError = ref<string | null>(null)

async function runKbSearch() {
  const q = kbSearchQuery.value.trim()
  if (q.length < 2 || kbSearching.value) return
  kbSearching.value = true
  kbSearchError.value = null
  try {
    kbSearchResults.value = await $fetch<ChunkSearchResult[]>(`/api/kb/${kbId}/search`, {
      headers: { Authorization: `Bearer ${auth.token}` },
      query: { q, mode: kbSearchMode.value, limit: 10 },
    })
    kbSearched.value = true
  } catch {
    kbSearchError.value = 'Search failed — is the KB indexed yet?'
  } finally {
    kbSearching.value = false
  }
}
const sources = ref<SourceOut[]>([])
const sourcesLoading = ref(false)
const urlInput = ref('')
const addingUrl = ref(false)
const urlError = ref<string | null>(null)
const dragging = ref(false)
const uploading = ref(false)
const uploadError = ref<string | null>(null)

// Polling: track in-progress source IDs to poll
const pollingIds = ref<Set<string>>(new Set())
let pollTimer: ReturnType<typeof setInterval> | null = null

async function fetchSources() {
  sourcesLoading.value = true
  try {
    sources.value = await $fetch<SourceOut[]>(`/api/kb/${kbId}/sources`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    // Re-enqueue any still-processing sources for polling
    for (const s of sources.value) {
      if (s.ingestion_status !== 'embedded' && s.ingestion_status !== 'failed') {
        pollingIds.value.add(s.id)
      }
    }
    if (pollingIds.value.size > 0) startPolling()
  } finally {
    sourcesLoading.value = false
  }
}

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    if (pollingIds.value.size === 0) { stopPolling(); return }
    const ids = [...pollingIds.value]
    for (const id of ids) {
      try {
        const s = await $fetch<SourceOut>(`/api/sources/${id}`, {
          headers: { Authorization: `Bearer ${auth.token}` },
        })
        const idx = sources.value.findIndex(x => x.id === id)
        if (idx !== -1) sources.value[idx] = { ...sources.value[idx], ...s }
        if (s.ingestion_status === 'embedded' || s.ingestion_status === 'failed') {
          pollingIds.value.delete(id)
        }
      } catch { pollingIds.value.delete(id) }
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function addUrl() {
  const url = urlInput.value.trim()
  if (!url || addingUrl.value) return
  addingUrl.value = true
  urlError.value = null
  try {
    const s = await $fetch<SourceOut>('/api/sources', {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { url, kb_id: kbId },
    })
    sources.value.unshift(s)
    urlInput.value = ''
    pollingIds.value.add(s.id)
    startPolling()
  } catch (err: unknown) {
    urlError.value = err instanceof Error ? err.message : 'Failed to add URL'
  } finally {
    addingUrl.value = false
  }
}

async function uploadFile(file: File) {
  uploading.value = true
  uploadError.value = null
  try {
    const form = new FormData()
    form.append('file', file)
    form.append('kb_id', kbId)
    const s = await $fetch<SourceOut>('/api/sources/upload', {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: form,
    })
    sources.value.unshift(s)
    pollingIds.value.add(s.id)
    startPolling()
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
  pending: 'text-warning',
  processing: 'text-warning',
  chunked: 'text-accent',
  embedded: 'text-grounded',
  failed: 'text-red-500',
}
const sourceTypeIcon: Record<string, string> = {
  pdf: '📄', web_page: '🌐', plain_text: '📝', epub: '📚',
}

onMounted(() => { fetchKBMeta(); fetchSources() })
onUnmounted(stopPolling)
</script>

<template>
  <div class="flex h-full overflow-hidden bg-surface">

    <!-- Left: tab content -->
    <div class="flex flex-col flex-1 min-w-0">

      <!-- Header + tabs -->
      <div class="px-6 pt-5 pb-0 border-b border-border">
        <div class="flex items-center gap-3 mb-4">
          <div class="flex-1 min-w-0">
            <h1 class="text-base font-semibold text-text-primary">
              {{ kbMeta?.title ?? 'Knowledge Base' }}
            </h1>
            <p class="text-xs mt-0.5 flex items-center gap-2">
              <span :class="kbMeta?.index_status === 'ready' ? 'text-grounded' : 'text-warning'">
                {{ kbMeta?.index_status ?? '…' }}
              </span>
              <ClientOnly>
                <button
                  v-if="kbMeta"
                  :disabled="!isOwner || updatingVisibility"
                  :title="visibilityTitle(kbMeta.visibility)"
                  class="px-2 py-0.5 rounded-full font-medium transition-colors"
                  :class="[visibilityColor[kbMeta.visibility] ?? 'text-text-muted bg-border', isOwner ? 'cursor-pointer hover:opacity-80' : 'cursor-default']"
                  @click="cycleVisibility"
                >
                  {{ kbMeta.visibility }}
                </button>
                <button
                  v-if="isOwner && kbMeta"
                  class="px-2 py-0.5 rounded-full font-medium text-text-muted bg-border hover:text-text-primary transition-colors"
                  title="Share this KB with specific users or teams"
                  @click="shareOpen = true"
                >
                  Share
                </button>
                <span v-if="!isOwner && kbMeta?.owner" class="text-text-muted">
                  by @{{ kbMeta.owner.handle }}
                </span>
              </ClientOnly>
            </p>
          </div>
          <NuxtLink
            :to="`/kb/${kbId}/learn`"
            class="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-grounded text-white hover:bg-green-700 transition-colors"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            Learn
          </NuxtLink>
        </div>

        <div class="flex gap-0">
          <button
            v-for="tab in (['query', 'search', 'sources'] as const)"
            :key="tab"
            class="px-4 py-2 text-sm border-b-2 transition-colors"
            :class="activeTab === tab
              ? 'border-accent text-accent font-medium'
              : 'border-transparent text-text-muted hover:text-text-secondary'"
            @click="activeTab = tab"
          >
            {{ tab === 'query' ? 'Ask' : tab === 'search' ? 'Search' : `Sources (${sources.length})` }}
          </button>
        </div>
      </div>

      <!-- Q&A tab -->
      <div v-show="activeTab === 'query'" class="flex flex-col flex-1 min-h-0 p-5">
        <div class="flex-1 overflow-y-auto rounded-xl border border-border bg-surface-secondary p-5 mb-4 min-h-[120px]">
          <p v-if="qaError" class="text-warning text-sm">{{ qaError }}</p>
          <p v-else-if="!response && !isStreaming" class="text-text-muted text-sm">
            Ask a question — answers are grounded in this KB's sources.
          </p>
          <div v-else class="font-prose text-text-primary text-sm leading-7" v-html="formatResponse(response)" />
          <span v-if="isStreaming" class="inline-block w-1.5 h-4 bg-accent animate-pulse align-middle ml-0.5" />
        </div>
        <form class="flex gap-3" @submit.prevent="handleSubmit">
          <input
            v-model="queryText"
            type="text"
            placeholder="Ask a question..."
            :disabled="isStreaming"
            class="flex-1 border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50 transition-colors"
          />
          <button
            type="submit"
            :disabled="isStreaming || !queryText.trim()"
            class="px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {{ isStreaming ? 'Thinking…' : 'Ask' }}
          </button>
        </form>
      </div>

      <!-- Search tab (KC-051) -->
      <div v-show="activeTab === 'search'" class="flex flex-col flex-1 min-h-0 p-5">
        <form class="flex gap-3 mb-4" @submit.prevent="runKbSearch">
          <input
            v-model="kbSearchQuery"
            type="text"
            :placeholder="kbSearchMode === 'semantic' ? 'Search this KB\'s sources by meaning…' : 'Search this KB\'s sources by keyword…'"
            :disabled="kbSearching"
            class="flex-1 border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50 transition-colors"
          />
          <select
            v-model="kbSearchMode"
            :disabled="kbSearching"
            class="border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary bg-surface focus:outline-none focus:border-accent disabled:opacity-50"
          >
            <option value="semantic">Semantic</option>
            <option value="keyword">Keyword</option>
          </select>
          <button
            type="submit"
            :disabled="kbSearching || kbSearchQuery.trim().length < 2"
            class="px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {{ kbSearching ? 'Searching…' : 'Search' }}
          </button>
        </form>

        <div class="flex-1 overflow-y-auto">
          <p v-if="kbSearchError" class="text-warning text-sm">{{ kbSearchError }}</p>
          <p v-else-if="!kbSearched" class="text-text-muted text-sm">
            Find passages by meaning — results come from this KB's indexed chunks, with source attribution.
          </p>
          <p v-else-if="kbSearchResults.length === 0" class="text-text-muted text-sm">
            No matching passages. Try different wording, or check the Sources tab that ingestion has completed.
          </p>
          <ul v-else class="space-y-3">
            <li
              v-for="r in kbSearchResults"
              :key="r.chunk_id"
              class="rounded-lg border border-grounded/20 bg-grounded-light p-4"
            >
              <div class="flex items-center justify-between gap-2 mb-1.5">
                <p class="text-xs font-medium text-text-primary truncate">
                  {{ r.source_title }}
                  <span class="text-text-muted font-normal ml-1">({{ r.source_type.replace('_', ' ') }})</span>
                </p>
                <p class="text-xs font-mono text-grounded shrink-0">{{ r.locator }}</p>
              </div>
              <p class="text-xs text-text-secondary leading-5 whitespace-pre-wrap break-words">{{ r.text }}</p>
            </li>
          </ul>
        </div>
      </div>

      <!-- Sources tab -->
      <div v-show="activeTab === 'sources'" class="flex flex-col flex-1 min-h-0 p-5 gap-4 overflow-y-auto">
        <!-- URL add (owner only) -->
        <div v-if="isOwner">
          <p class="text-xs font-medium text-text-secondary mb-2">Add a URL</p>
          <form class="flex gap-2" @submit.prevent="addUrl">
            <input
              v-model="urlInput"
              type="url"
              placeholder="https://example.com/article"
              :disabled="addingUrl"
              class="flex-1 border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50 transition-colors"
            />
            <button
              type="submit"
              :disabled="addingUrl || !urlInput.trim()"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
            >
              {{ addingUrl ? 'Adding…' : 'Add' }}
            </button>
          </form>
          <p v-if="urlError" class="text-xs text-warning mt-1.5">{{ urlError }}</p>
        </div>

        <!-- File upload (owner only) -->
        <div v-if="isOwner">
          <p class="text-xs font-medium text-text-secondary mb-2">Upload a file</p>
          <label
            class="block rounded-xl border-2 border-dashed p-6 text-center cursor-pointer transition-colors"
            :class="dragging ? 'border-accent bg-accent/5' : 'border-border hover:border-accent/50'"
            @dragover.prevent="dragging = true"
            @dragleave="dragging = false"
            @drop.prevent="onDrop"
          >
            <input type="file" class="sr-only" accept=".pdf,.txt,.md,.docx" :disabled="uploading" @change="onFileInput" />
            <p v-if="uploading" class="text-sm text-text-muted animate-pulse">Uploading…</p>
            <p v-else class="text-sm text-text-muted">
              Drop a PDF or text file here, or <span class="text-accent">browse</span>
            </p>
            <p class="text-xs text-text-muted mt-1">PDF, TXT, MD, DOCX — max 200MB</p>
          </label>
          <p v-if="uploadError" class="text-xs text-warning mt-1.5">{{ uploadError }}</p>
        </div>

        <!-- Source list -->
        <div>
          <p class="text-xs font-medium text-text-secondary mb-2">
            Indexed sources
            <span v-if="sourcesLoading" class="ml-1 text-text-muted">(loading…)</span>
          </p>
          <p v-if="!sourcesLoading && sources.length === 0" class="text-xs text-text-muted">
            No sources yet — add a URL or upload a file above.
          </p>
          <ul class="space-y-2">
            <li
              v-for="s in sources"
              :key="s.id"
              class="flex items-center gap-3 rounded-lg border border-border bg-surface p-3"
            >
              <span class="text-base shrink-0">{{ sourceTypeIcon[s.type] ?? '📎' }}</span>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-text-primary truncate">{{ s.title }}</p>
                <p class="text-xs mt-0.5" :class="statusColor[s.ingestion_status] ?? 'text-text-muted'">
                  {{ s.ingestion_status }}
                  <span v-if="pollingIds.has(s.id)" class="ml-1 inline-block w-1 h-1 rounded-full bg-current animate-bounce" />
                </p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Citations sidebar (Q&A tab only) -->
    <aside
      v-if="activeTab === 'query' && citationList.length > 0"
      class="w-64 shrink-0 border-l border-border bg-surface overflow-y-auto p-4"
    >
      <h2 class="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
        Sources ({{ citationList.length }})
      </h2>
      <ul class="space-y-3">
        <li
          v-for="c in citationList"
          :key="c.chunk_id"
          class="rounded-lg border border-grounded/20 bg-grounded-light p-3"
        >
          <p class="text-xs font-mono text-grounded mb-1">{{ c.locator }}</p>
          <p class="text-xs text-text-secondary leading-5 line-clamp-4">{{ c.excerpt }}</p>
        </li>
      </ul>
    </aside>

    <ShareDialog
      v-if="shareOpen && kbMeta"
      resource-type="kbs"
      :resource-id="kbId"
      :resource-title="kbMeta.title"
      @close="shareOpen = false"
    />
  </div>
</template>
