<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useStreamingQuery } from '~/composables/useStreamingQuery'
import { videoDeepLink } from '~/utils/video'

const route = useRoute()
const auth = useAuthStore()
const kbId = route.params.kbId as string

interface KBMeta {
  id: string
  title: string
  index_status: string
  visibility: string
  owner: { id: string; handle: string; display_name: string } | null
  editable: boolean
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

// Owner or editor grant — server-computed (docs/22, OQ-93). Editors have had
// backend write access since KC-067; the UI finally follows.
const canEdit = computed(() => isOwner.value || kbMeta.value?.editable === true)

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
  // Match both [SOURCE:uuid] (the prompt contract) and bare [uuid] — the
  // local model sometimes omits the prefix (learn-page precedent)
  return text
    .replace(
      /\[SOURCE:([a-f0-9-]{36})\]/g,
      '<sup class="text-grounded font-mono text-xs">[src]</sup>'
    )
    .replace(
      /\[([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\]/g,
      '<sup class="text-grounded font-mono text-xs">[src]</sup>'
    )
}

// ── Sources ───────────────────────────────────────────────────────────────────

interface SourceOut {
  id: string; type: string; title: string; ingestion_status: string; created_at: string
}

const activeTab = ref<'query' | 'search' | 'compare' | 'sources'>('query')

// ── Multi-source synthesis (KC-097, docs/16) ────────────────────────────────

const {
  response: compareResponse,
  citations: compareCitations,
  isStreaming: compareStreaming,
  error: compareError,
  submit: compareSubmit,
} = useStreamingQuery(kbId, 'synthesize')

const compareQuestion = ref('')
const compareSelected = ref<Set<string>>(new Set())

function toggleCompareSource(id: string) {
  const next = new Set(compareSelected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  compareSelected.value = next
}

const compareReady = computed(() =>
  compareQuestion.value.trim().length > 0
  && compareSelected.value.size >= 2
  && compareSelected.value.size <= 5
  && !compareStreaming.value,
)

// The question/sources the current answer was generated from — the inputs
// may be edited after submission, but Save must persist what actually ran
const lastRun = ref<{ question: string; sourceIds: string[] } | null>(null)

async function handleCompare() {
  if (!compareReady.value) return
  const question = compareQuestion.value.trim()
  const sourceIds = [...compareSelected.value]
  lastRun.value = { question, sourceIds }
  synthSaved.value = false
  await compareSubmit(question, sourceIds)
}

// ── Saved syntheses (KC-101, docs/17) ───────────────────────────────────────

interface SavedSynthesis {
  id: string
  kb_id: string
  question: string
  answer_text: string
  citations: { chunk_id: string; source_id: string; locator: string; excerpt: string }[]
  source_ids: string[]
  created_at: string
}

const savedSyntheses = ref<SavedSynthesis[]>([])
const savedLoaded = ref(false)
const synthSaving = ref(false)
const synthSaved = ref(false)
const expandedSynthesis = ref<string | null>(null)

async function loadSavedSyntheses() {
  if (savedLoaded.value) return
  savedLoaded.value = true
  try {
    savedSyntheses.value = await $fetch<SavedSynthesis[]>(`/api/kb/${kbId}/syntheses`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
  } catch {
    savedLoaded.value = false
  }
}

watch(activeTab, (t) => { if (t === 'compare') loadSavedSyntheses() })

async function saveSynthesis() {
  if (synthSaving.value || !lastRun.value || !compareResponse.value) return
  synthSaving.value = true
  try {
    const row = await $fetch<SavedSynthesis>(`/api/kb/${kbId}/syntheses` as string, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: {
        question: lastRun.value.question,
        source_ids: lastRun.value.sourceIds,
        answer_text: compareResponse.value,
        citations: compareCitationList.value.map(c => ({
          chunk_id: c.chunk_id,
          source_id: c.source_id,
          locator: c.locator,
          excerpt: (c.excerpt ?? '').slice(0, 500),
        })),
      },
    })
    savedSyntheses.value = [row, ...savedSyntheses.value]
    synthSaved.value = true
  } catch {
    // leave the button enabled; the user can retry
  } finally {
    synthSaving.value = false
  }
}

async function deleteSynthesis(id: string) {
  try {
    await $fetch(`/api/kb/${kbId}/syntheses/${id}` as string, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    savedSyntheses.value = savedSyntheses.value.filter(s => s.id !== id)
  } catch {
    // keep the row; the user can retry
  }
}

// Add a saved synthesis to one of my boards (asset-detail precedent, KC-046)
interface BoardSummary { id: string; title: string }

const abForSynthesis = ref<string | null>(null)  // synthesis id the picker is open for
const myBoards = ref<BoardSummary[]>([])
const abBoardId = ref('')
const abSaving = ref(false)
const abMessage = ref<string | null>(null)

async function openBoardPicker(synthesisId: string) {
  abForSynthesis.value = abForSynthesis.value === synthesisId ? null : synthesisId
  abMessage.value = null
  if (myBoards.value.length === 0) {
    try {
      myBoards.value = await $fetch<BoardSummary[]>('/api/my/boards', {
        headers: { Authorization: `Bearer ${auth.token}` },
      })
      if (myBoards.value.length > 0) abBoardId.value = myBoards.value[0].id
    } catch {
      abMessage.value = 'Could not load your boards'
    }
  }
}

async function addSynthesisToBoard(synthesisId: string) {
  if (abSaving.value || !abBoardId.value) return
  abSaving.value = true
  abMessage.value = null
  try {
    await $fetch(`/api/boards/${abBoardId.value}/syntheses` as string, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { synthesis_id: synthesisId },
    })
    const board = myBoards.value.find(b => b.id === abBoardId.value)
    abMessage.value = `Added to “${board?.title ?? 'board'}”`
  } catch (err: unknown) {
    const detail = (err as { data?: { detail?: string } })?.data?.detail
    abMessage.value = typeof detail === 'string' ? detail : 'Failed to add to board'
  } finally {
    abSaving.value = false
  }
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

const compareCitationList = computed(() =>
  Object.values(compareCitations.value) as Array<{
    chunk_id: string; source_id: string; locator: string; excerpt: string
  }>
)

const sidebarCitations = computed(() =>
  activeTab.value === 'compare' ? compareCitationList.value : citationList.value
)

// ── KB search (KC-051) ──────────────────────────────────────────────────────

interface ChunkSearchResult {
  chunk_id: string
  source_id: string
  source_title: string
  source_type: string
  source_url: string | null
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

// Only embedded sources can be compared — the others have no chunks yet
const embeddedSources = computed(() => sources.value.filter(s => s.ingestion_status === 'embedded'))
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
  pdf: '📄', web_page: '🌐', plain_text: '📝', epub: '📚', video: '🎬', prompt_asset: '🧩', synthesis: '⚗️',
}

// ── Bundle export (KC-105, docs/18) ─────────────────────────────────────────

const exporting = ref(false)

async function exportKB() {
  if (exporting.value) return
  exporting.value = true
  try {
    const res = await fetch(`/api/kb/${kbId}/export`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    if (!res.ok) throw new Error(`Export failed: ${res.status}`)
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    const match = /filename="([^"]+)"/.exec(res.headers.get('Content-Disposition') ?? '')
    a.download = match?.[1] ?? 'kb.knomms.json'
    a.click()
    URL.revokeObjectURL(a.href)
  } catch {
    // no dedicated error surface in the header; the button simply re-enables
  } finally {
    exporting.value = false
  }
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
                <button
                  v-if="isOwner && kbMeta"
                  :disabled="exporting"
                  class="px-2 py-0.5 rounded-full font-medium text-text-muted bg-border hover:text-text-primary disabled:opacity-50 transition-colors"
                  title="Download this KB as a portable bundle"
                  @click="exportKB"
                >
                  {{ exporting ? 'Exporting…' : 'Export' }}
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
            v-for="tab in (['query', 'search', 'compare', 'sources'] as const)"
            :key="tab"
            class="px-4 py-2 text-sm border-b-2 transition-colors"
            :class="activeTab === tab
              ? 'border-accent text-accent font-medium'
              : 'border-transparent text-text-muted hover:text-text-secondary'"
            @click="activeTab = tab"
          >
            {{ tab === 'query' ? 'Ask' : tab === 'search' ? 'Search' : tab === 'compare' ? 'Compare' : `Sources (${sources.length})` }}
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

      <!-- Compare tab (KC-097, docs/16) -->
      <div v-show="activeTab === 'compare'" class="flex flex-col flex-1 min-h-0 p-5">
        <div class="mb-4">
          <p class="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
            Sources to compare (2–5)
          </p>
          <p v-if="embeddedSources.length < 2" class="text-sm text-text-muted">
            Comparison needs at least two embedded sources in this KB.
          </p>
          <div v-else class="flex flex-wrap gap-2">
            <label
              v-for="s in embeddedSources"
              :key="s.id"
              class="flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs cursor-pointer transition-colors"
              :class="compareSelected.has(s.id)
                ? 'border-accent bg-accent/5 text-text-primary'
                : 'border-border text-text-secondary hover:border-accent/40'"
            >
              <input
                type="checkbox"
                class="accent-current"
                :checked="compareSelected.has(s.id)"
                :disabled="compareStreaming"
                @change="toggleCompareSource(s.id)"
              />
              <span>{{ sourceTypeIcon[s.type] ?? '📎' }}</span>
              <span class="max-w-[16rem] truncate">{{ s.title }}</span>
            </label>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto rounded-xl border border-border bg-surface-secondary p-5 mb-4 min-h-[120px]">
          <p v-if="compareError" class="text-warning text-sm">{{ compareError }}</p>
          <p v-else-if="!compareResponse && !compareStreaming" class="text-text-muted text-sm">
            Pick two or more sources and ask how they relate — agreements, disagreements, unique claims. Every claim is cited per source.
          </p>
          <div v-else class="font-prose text-text-primary text-sm leading-7" v-html="formatResponse(compareResponse)" />
          <span v-if="compareStreaming" class="inline-block w-1.5 h-4 bg-accent animate-pulse align-middle ml-0.5" />
        </div>
        <form class="flex gap-3" @submit.prevent="handleCompare">
          <input
            v-model="compareQuestion"
            type="text"
            placeholder="What should these sources be compared on?"
            :disabled="compareStreaming"
            class="flex-1 border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50 transition-colors"
          />
          <button
            v-if="compareResponse && !compareStreaming && lastRun"
            type="button"
            :disabled="synthSaving || synthSaved"
            class="px-4 py-2.5 rounded-lg text-sm font-medium border border-grounded text-grounded hover:bg-grounded/10 disabled:opacity-50 transition-colors"
            @click="saveSynthesis"
          >
            {{ synthSaved ? '✓ Saved' : synthSaving ? 'Saving…' : 'Save' }}
          </button>
          <button
            type="submit"
            :disabled="!compareReady"
            class="px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {{ compareStreaming ? 'Comparing…' : 'Compare' }}
          </button>
        </form>

        <!-- Saved syntheses (KC-101) -->
        <div v-if="savedSyntheses.length > 0" class="mt-6">
          <p class="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
            Saved syntheses ({{ savedSyntheses.length }})
          </p>
          <ul class="space-y-2">
            <li
              v-for="s in savedSyntheses"
              :key="s.id"
              class="rounded-xl border border-border p-3"
            >
              <div class="flex items-center justify-between gap-3">
                <button
                  class="flex-1 min-w-0 text-left text-sm text-text-primary font-medium truncate hover:text-accent"
                  @click="expandedSynthesis = expandedSynthesis === s.id ? null : s.id"
                >
                  ⚗️ {{ s.question }}
                </button>
                <span class="text-xs text-text-muted shrink-0">{{ fmtDate(s.created_at) }}</span>
                <button
                  class="text-xs text-text-secondary hover:text-accent shrink-0"
                  @click="openBoardPicker(s.id)"
                >
                  Add to board
                </button>
                <button
                  class="text-xs text-text-muted hover:text-warning shrink-0"
                  title="Delete this saved synthesis"
                  @click="deleteSynthesis(s.id)"
                >
                  ✕
                </button>
              </div>

              <div v-if="abForSynthesis === s.id" class="mt-2 flex items-center gap-2">
                <select
                  v-model="abBoardId"
                  class="text-xs border border-border rounded-lg px-2 py-1.5 bg-surface text-text-secondary focus:outline-none focus:border-accent"
                >
                  <option v-for="b in myBoards" :key="b.id" :value="b.id">{{ b.title }}</option>
                </select>
                <button
                  :disabled="abSaving || !abBoardId"
                  class="text-xs px-3 py-1.5 rounded-lg bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
                  @click="addSynthesisToBoard(s.id)"
                >
                  {{ abSaving ? 'Adding…' : 'Add' }}
                </button>
                <span v-if="abMessage" class="text-xs text-text-muted">{{ abMessage }}</span>
              </div>

              <div v-if="expandedSynthesis === s.id" class="mt-3 border-t border-border pt-3">
                <div class="font-prose text-text-primary text-sm leading-7" v-html="formatResponse(s.answer_text)" />
                <p class="text-xs text-text-muted mt-2">
                  {{ s.citations.length }} citation{{ s.citations.length !== 1 ? 's' : '' }} ·
                  {{ s.source_ids.length }} sources compared
                </p>
              </div>
            </li>
          </ul>
        </div>
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
                <a
                  v-if="r.source_type === 'video' && videoDeepLink(r.source_url, r.locator)"
                  :href="videoDeepLink(r.source_url, r.locator)!"
                  target="_blank"
                  rel="noopener"
                  class="text-xs font-mono text-grounded shrink-0 underline decoration-dotted hover:text-accent"
                  title="Open the video at this timestamp"
                >▶ {{ r.locator }}</a>
                <p v-else class="text-xs font-mono text-grounded shrink-0">{{ r.locator }}</p>
              </div>
              <p class="text-xs text-text-secondary leading-5 whitespace-pre-wrap break-words">{{ r.text }}</p>
            </li>
          </ul>
        </div>
      </div>

      <!-- Sources tab -->
      <div v-show="activeTab === 'sources'" class="flex flex-col flex-1 min-h-0 p-5 gap-4 overflow-y-auto">
        <!-- URL add (owner or editor grant) -->
        <div v-if="canEdit">
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

        <!-- File upload (owner or editor grant) -->
        <div v-if="canEdit">
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

    <!-- Citations sidebar (Ask + Compare tabs) -->
    <aside
      v-if="(activeTab === 'query' || activeTab === 'compare') && sidebarCitations.length > 0"
      class="w-64 shrink-0 border-l border-border bg-surface overflow-y-auto p-4"
    >
      <h2 class="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
        Sources ({{ sidebarCitations.length }})
      </h2>
      <ul class="space-y-3">
        <li
          v-for="c in sidebarCitations"
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
