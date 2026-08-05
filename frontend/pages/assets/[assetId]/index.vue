<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

import { ref, computed, onMounted, watch } from 'vue'

const route = useRoute()
const assetId = route.params.assetId as string
const auth = useAuthStore()

interface AssetOwner {
  id: string
  handle: string
  display_name: string
}

interface AssetVersion {
  id: string
  asset_id: string
  version_num: number
  content: string
  content_hash: string
  rationale: string
  tags: string[] | null
  model_pin: string | null
  status: string
  created_by: string
  created_at: string
}

interface AssetOut {
  id: string
  title: string
  description: string
  asset_type: string
  visibility: string
  fork_count: number
  forked_from_id: string | null
  fork_lineage: string[]
  created_at: string
  updated_at: string
  owner: AssetOwner | null
  versions: AssetVersion[]
}

const asset = ref<AssetOut | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const deprecatedModels = ref<string[]>([])

// Selected version for main view
const selectedVersionNum = ref<number | null>(null)
const selectedVersion = computed(() =>
  asset.value?.versions.find(v => v.version_num === selectedVersionNum.value) ?? null
)

// Diff state
const showDiff = ref(false)
const diffFromNum = ref<number | null>(null)
const diffToNum = ref<number | null>(null)
const diffFromVersion = computed(() =>
  asset.value?.versions.find(v => v.version_num === diffFromNum.value) ?? null
)
const diffToVersion = computed(() =>
  asset.value?.versions.find(v => v.version_num === diffToNum.value) ?? null
)

// Deprecate state
const deprecating = ref<number | null>(null)
const deprecateError = ref<string | null>(null)

// ── Eval cases (KC-043) ──────────────────────────────────────────────────────

interface EvalCase {
  id: string
  asset_version_id: string
  input: string
  expected_output: string
  grading_strategy: string
  grading_config: Record<string, string> | null
  created_at: string
}

const casesByVersion = ref<Record<number, EvalCase[] | undefined>>({})
const casesLoading = ref(false)

const versionCases = computed(() =>
  selectedVersionNum.value !== null ? casesByVersion.value[selectedVersionNum.value] : undefined
)

async function fetchCases(versionNum: number) {
  if (casesByVersion.value[versionNum] !== undefined) return
  casesLoading.value = true
  try {
    casesByVersion.value[versionNum] = await $fetch<EvalCase[]>(
      `/api/assets/${assetId}/versions/${versionNum}/cases`,
      { headers: { Authorization: `Bearer ${auth.token}` } },
    )
  } catch {
    casesByVersion.value[versionNum] = []
  } finally {
    casesLoading.value = false
  }
}

watch(selectedVersionNum, (num) => {
  if (num !== null && asset.value?.asset_type === 'eval_suite') fetchCases(num)
})

// ── Visibility editing (KC-056) ─────────────────────────────────────────────

const updatingVisibility = ref(false)
async function cycleVisibility() {
  if (!isOwner.value || updatingVisibility.value || !asset.value) return
  const order = ['private', 'team', 'public']
  const next = order[(order.indexOf(asset.value.visibility) + 1) % order.length]
  updatingVisibility.value = true
  try {
    const updated = await $fetch<AssetOut>(`/api/assets/${assetId}`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { visibility: next },
    })
    asset.value = { ...asset.value, visibility: updated.visibility }
  } catch {
    // badge simply doesn't change
  } finally {
    updatingVisibility.value = false
  }
}

// ── Add to board (KC-046) ────────────────────────────────────────────────────

interface BoardSummary {
  id: string
  title: string
  item_count?: number
}

const showAddToBoard = ref(false)
const myBoards = ref<BoardSummary[]>([])
const boardsLoading = ref(false)
const abBoardId = ref('')
const abLane = ref('')
const abNote = ref('')
const abSaving = ref(false)
const abError = ref<string | null>(null)
const abSuccess = ref<string | null>(null)

async function openAddToBoard() {
  abError.value = null
  abSuccess.value = null
  abLane.value = ''
  abNote.value = ''
  showAddToBoard.value = true
  if (myBoards.value.length === 0) {
    boardsLoading.value = true
    try {
      myBoards.value = await $fetch<BoardSummary[]>('/api/my/boards', {
        headers: { Authorization: `Bearer ${auth.token}` },
      })
      if (myBoards.value.length > 0) abBoardId.value = myBoards.value[0].id
    } catch {
      abError.value = 'Could not load your boards'
    } finally {
      boardsLoading.value = false
    }
  }
}

async function submitAddToBoard() {
  if (abSaving.value || !abBoardId.value || !selectedVersion.value) return
  abSaving.value = true
  abError.value = null
  try {
    await $fetch(`/api/boards/${abBoardId.value}/assets`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: {
        asset_id: assetId,
        version_num: selectedVersion.value.version_num,
        note: abNote.value,
        lane: abLane.value,
      },
    })
    const board = myBoards.value.find(b => b.id === abBoardId.value)
    abSuccess.value = `v${selectedVersion.value.version_num} added to “${board?.title ?? 'board'}”`
  } catch (err: unknown) {
    const detail = (err as { data?: { detail?: string } })?.data?.detail
    abError.value = typeof detail === 'string' ? detail : 'Failed to add to board'
  } finally {
    abSaving.value = false
  }
}

// ── New version composer (KC-043) ────────────────────────────────────────────

interface CaseDraft {
  input: string
  expected_output: string
  grading_strategy: string
  pattern: string
}

const GRADING_STRATEGIES = ['exact_match', 'contains', 'regex', 'llm_judge']

const showNewVersion = ref(false)
const nvContent = ref('')
const nvRationale = ref('')
const nvModelPin = ref('')
const nvCases = ref<CaseDraft[]>([])
const nvSaving = ref(false)
const nvError = ref<string | null>(null)

function openNewVersion() {
  nvContent.value = selectedVersion.value?.content ?? ''
  nvRationale.value = ''
  nvModelPin.value = selectedVersion.value?.model_pin ?? ''
  nvCases.value = (versionCases.value ?? []).map(c => ({
    input: c.input,
    expected_output: c.expected_output,
    grading_strategy: c.grading_strategy,
    pattern: c.grading_config?.pattern ?? '',
  }))
  nvError.value = null
  showNewVersion.value = true
}

function addCaseRow() {
  nvCases.value.push({ input: '', expected_output: '', grading_strategy: 'exact_match', pattern: '' })
}

function removeCaseRow(idx: number) {
  nvCases.value.splice(idx, 1)
}

async function submitNewVersion() {
  if (nvSaving.value || !nvContent.value.trim()) return
  nvSaving.value = true
  nvError.value = null
  try {
    const evalCases = asset.value?.asset_type === 'eval_suite'
      ? nvCases.value.map(c => ({
          input: c.input,
          expected_output: c.expected_output,
          grading_strategy: c.grading_strategy,
          grading_config: c.grading_strategy === 'regex' && c.pattern ? { pattern: c.pattern } : null,
        }))
      : []
    const created = await $fetch<AssetVersion>(`/api/assets/${assetId}/versions`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: {
        content: nvContent.value,
        rationale: nvRationale.value,
        tags: [],
        model_pin: nvModelPin.value.trim() || null,
        eval_cases: evalCases,
      },
    })
    showNewVersion.value = false
    casesByVersion.value = {}
    await fetchAsset()
    selectedVersionNum.value = created.version_num
  } catch (err: unknown) {
    const detail = (err as { data?: { detail?: string } })?.data?.detail
    nvError.value = typeof detail === 'string' ? detail : 'Failed to create version'
  } finally {
    nvSaving.value = false
  }
}

const isOwner = computed(() =>
  auth.isLoggedIn && asset.value?.owner?.id === auth.user?.id
)

// Sorted versions newest-first for timeline, but version detail shows selected
const sortedVersions = computed(() =>
  [...(asset.value?.versions ?? [])].sort((a, b) => b.version_num - a.version_num)
)

function isDeprecated(pin: string | null, list: string[]): boolean {
  if (!pin) return false
  return list.includes(pin) || list.includes(pin.split(':')[0])
}

const hasDrift = computed(() =>
  (asset.value?.versions ?? []).some(v => isDeprecated(v.model_pin, deprecatedModels.value))
)

async function fetchAsset() {
  loading.value = true
  error.value = null
  try {
    asset.value = await $fetch<AssetOut>(`/api/assets/${assetId}`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    // Default to latest version
    if (asset.value.versions.length > 0) {
      selectedVersionNum.value = Math.max(...asset.value.versions.map(v => v.version_num))
    }
  } catch {
    error.value = 'Asset not found or you do not have access.'
  } finally {
    loading.value = false
  }
}

async function deprecateVersion(versionNum: number) {
  if (deprecating.value !== null) return
  deprecating.value = versionNum
  deprecateError.value = null
  try {
    const updated = await $fetch<AssetVersion>(`/api/assets/${assetId}/versions/${versionNum}/deprecate`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    if (asset.value) {
      asset.value = {
        ...asset.value,
        versions: asset.value.versions.map(v => v.version_num === versionNum ? updated : v),
      }
    }
  } catch {
    deprecateError.value = 'Failed to deprecate version'
  } finally {
    deprecating.value = null
  }
}

function openDiff(fromNum: number, toNum: number) {
  diffFromNum.value = fromNum
  diffToNum.value = toNum
  showDiff.value = true
}

// ── Line-based diff (LCS algorithm) ──────────────────────────────────────────

interface DiffLine {
  type: 'unchanged' | 'added' | 'removed'
  line: string
}

function computeDiff(oldText: string, newText: string): DiffLine[] {
  const a = oldText.split('\n')
  const b = newText.split('\n')
  const m = a.length
  const n = b.length

  // Build LCS DP table
  const dp: number[][] = []
  for (let i = 0; i <= m; i++) {
    dp.push(new Array(n + 1).fill(0))
  }
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) dp[i][j] = dp[i - 1][j - 1] + 1
      else dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1])
    }
  }

  // Backtrack to get diff
  const result: DiffLine[] = []
  let i = m
  let j = n
  const ops: DiffLine[] = []

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      ops.push({ type: 'unchanged', line: a[i - 1] })
      i--
      j--
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      ops.push({ type: 'added', line: b[j - 1] })
      j--
    } else {
      ops.push({ type: 'removed', line: a[i - 1] })
      i--
    }
  }

  return ops.reverse()
}

const diffLines = computed<DiffLine[]>(() => {
  if (!diffFromVersion.value || !diffToVersion.value) return []
  return computeDiff(diffFromVersion.value.content, diffToVersion.value.content)
})

const typeLabel: Record<string, string> = {
  system_prompt: 'System Prompt',
  few_shot_set: 'Few-Shot Set',
  eval_suite: 'Eval Suite',
  chain_spec: 'Chain Spec',
  tool_spec: 'Tool Spec',
}

const statusColor: Record<string, string> = {
  draft: 'text-text-muted bg-border',
  active: 'text-grounded bg-grounded/10',
  deprecated: 'text-warning bg-warning/10',
}

const visibilityColor: Record<string, string> = {
  private: 'text-text-muted bg-border',
  team: 'text-accent bg-accent/10',
  public: 'text-grounded bg-grounded/10',
}

function visibilityTitle(v: string): string | undefined {
  const parts: string[] = []
  if (v === 'team') parts.push('Team — visible to members of your organisation')
  if (isOwner.value) parts.push('Click to change visibility')
  return parts.join(' · ') || undefined
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

onMounted(async () => {
  const [_, res] = await Promise.all([
    fetchAsset(),
    $fetch<{ deprecated: string[] }>('/api/deprecated-models').catch(() => ({ deprecated: [] })),
  ])
  deprecatedModels.value = res.deprecated
})
</script>

<template>
  <div class="min-h-screen bg-surface">
    <div v-if="loading" class="flex items-center justify-center py-32">
      <div class="text-sm text-text-muted">Loading…</div>
    </div>

    <div v-else-if="error" class="text-center py-20 text-warning text-sm">
      {{ error }}
    </div>

    <template v-else-if="asset">
      <!-- Asset header -->
      <div class="border-b border-border bg-surface">
        <div class="max-w-5xl mx-auto px-6 py-8">
          <div class="flex items-start gap-4">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-2">
                <NuxtLink to="/assets" class="text-xs text-text-muted hover:text-accent transition-colors">
                  ← AI Assets
                </NuxtLink>
              </div>
              <h1 class="text-2xl font-semibold text-text-primary mb-2">{{ asset.title }}</h1>
              <p v-if="asset.description" class="text-sm text-text-secondary leading-6 max-w-2xl mb-3">
                {{ asset.description }}
              </p>
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-xs px-2 py-0.5 rounded-full font-medium bg-border text-text-secondary">
                  {{ typeLabel[asset.asset_type] ?? asset.asset_type }}
                </span>
                <ClientOnly>
                  <button
                    :disabled="!isOwner || updatingVisibility"
                    :title="visibilityTitle(asset.visibility)"
                    class="text-xs px-2 py-0.5 rounded-full font-medium transition-colors"
                    :class="[visibilityColor[asset.visibility], isOwner ? 'cursor-pointer hover:opacity-80' : 'cursor-default']"
                    @click="cycleVisibility"
                  >
                    {{ asset.visibility }}
                  </button>
                </ClientOnly>
                <span class="text-xs text-text-muted">
                  {{ asset.versions.length }} version{{ asset.versions.length !== 1 ? 's' : '' }}
                </span>
                <span v-if="asset.fork_count > 0" class="text-xs text-text-muted">
                  · {{ asset.fork_count }} fork{{ asset.fork_count !== 1 ? 's' : '' }}
                </span>
                <span v-if="asset.owner" class="text-xs text-text-muted">
                  · by @{{ asset.owner.handle }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Drift alert -->
      <div v-if="hasDrift" class="max-w-5xl mx-auto px-6 pt-5">
        <div class="flex items-start gap-3 rounded-lg border border-warning/40 bg-warning/5 px-4 py-3">
          <svg class="w-4 h-4 text-warning shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          </svg>
          <p class="text-xs text-warning leading-5">
            One or more versions are pinned to deprecated models. Eval results may drift — commit a new version with an updated model pin.
          </p>
        </div>
      </div>

      <!-- Body: timeline + content -->
      <div class="max-w-5xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8">

        <!-- Version history timeline (left column) -->
        <aside class="lg:col-span-1">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-xs font-semibold text-text-secondary uppercase tracking-wider">Version history</h2>
            <ClientOnly>
              <button
                v-if="isOwner"
                class="text-xs px-2.5 py-1 rounded-lg font-medium bg-accent text-white hover:bg-accent-hover transition-colors"
                @click="openNewVersion"
              >
                + New version
              </button>
            </ClientOnly>
          </div>

          <div v-if="asset.versions.length === 0" class="text-sm text-text-muted">No versions yet.</div>

          <ul v-else class="space-y-2">
            <li
              v-for="v in sortedVersions"
              :key="v.version_num"
              class="relative"
            >
              <!-- Timeline connector line -->
              <div v-if="sortedVersions.indexOf(v) < sortedVersions.length - 1"
                class="absolute left-3.5 top-8 bottom-[-0.5rem] w-px bg-border z-0" />

              <button
                class="relative z-10 w-full text-left rounded-lg border px-3 py-2.5 transition-all"
                :class="selectedVersionNum === v.version_num
                  ? 'border-accent bg-accent/5'
                  : 'border-border bg-surface hover:border-accent/30'"
                @click="selectedVersionNum = v.version_num"
              >
                <div class="flex items-center gap-2">
                  <!-- Version dot -->
                  <div
                    class="w-2 h-2 rounded-full shrink-0"
                    :class="v.status === 'deprecated' ? 'bg-warning' : v.status === 'active' ? 'bg-grounded' : 'bg-text-muted'"
                  />
                  <span class="text-sm font-medium text-text-primary">v{{ v.version_num }}</span>
                  <span class="text-xs px-1.5 py-0.5 rounded-full font-medium ml-auto" :class="statusColor[v.status] ?? 'text-text-muted bg-border'">
                    {{ v.status }}
                  </span>
                </div>
                <p v-if="v.rationale" class="text-xs text-text-muted mt-1 line-clamp-2 pl-4">{{ v.rationale }}</p>
                <p class="text-xs text-text-muted mt-1 pl-4">{{ formatDate(v.created_at) }}</p>
                <!-- Model pin badge -->
                <div v-if="v.model_pin" class="mt-1 pl-4">
                  <ModelPinBadge :model-pin="v.model_pin" :deprecated="isDeprecated(v.model_pin, deprecatedModels)" />
                </div>
              </button>
            </li>
          </ul>

          <!-- Diff selector -->
          <div v-if="asset.versions.length >= 2" class="mt-6">
            <h3 class="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Compare versions</h3>
            <div class="flex items-center gap-2">
              <select
                v-model="diffFromNum"
                class="flex-1 border border-border rounded-lg px-2 py-1.5 text-sm text-text-primary bg-surface focus:outline-none focus:border-accent"
              >
                <option :value="null" disabled>From</option>
                <option v-for="v in sortedVersions" :key="v.version_num" :value="v.version_num">v{{ v.version_num }}</option>
              </select>
              <span class="text-text-muted text-xs">→</span>
              <select
                v-model="diffToNum"
                class="flex-1 border border-border rounded-lg px-2 py-1.5 text-sm text-text-primary bg-surface focus:outline-none focus:border-accent"
              >
                <option :value="null" disabled>To</option>
                <option v-for="v in sortedVersions" :key="v.version_num" :value="v.version_num">v{{ v.version_num }}</option>
              </select>
            </div>
            <button
              :disabled="diffFromNum === null || diffToNum === null || diffFromNum === diffToNum"
              class="mt-2 w-full px-3 py-1.5 rounded-lg text-sm font-medium border border-border text-text-secondary hover:bg-surface-secondary disabled:opacity-40 transition-colors"
              @click="diffFromNum !== null && diffToNum !== null && openDiff(diffFromNum, diffToNum)"
            >
              Show diff
            </button>
          </div>
        </aside>

        <!-- Version content (right 2 columns) -->
        <main class="lg:col-span-2">
          <div v-if="!selectedVersion" class="text-sm text-text-muted py-4">
            Select a version to view its content.
          </div>

          <template v-else>
            <div class="flex items-center justify-between mb-3">
              <h2 class="text-sm font-semibold text-text-primary">
                Version {{ selectedVersion.version_num }} content
              </h2>
              <div class="flex items-center gap-2">
                <ClientOnly>
                  <button
                    v-if="isOwner"
                    class="text-xs px-3 py-1.5 rounded-lg border border-border text-text-secondary hover:bg-surface-secondary transition-colors"
                    @click="openAddToBoard"
                  >
                    Add to board
                  </button>
                  <button
                    v-if="isOwner && selectedVersion.status !== 'deprecated'"
                    :disabled="deprecating === selectedVersion.version_num"
                    class="text-xs px-3 py-1.5 rounded-lg border border-border text-text-muted hover:bg-surface-secondary disabled:opacity-50 transition-colors"
                    @click="deprecateVersion(selectedVersion.version_num)"
                  >
                    {{ deprecating === selectedVersion.version_num ? 'Deprecating…' : 'Deprecate' }}
                  </button>
                </ClientOnly>
              </div>
            </div>

            <p v-if="deprecateError" class="text-xs text-warning mb-3">{{ deprecateError }}</p>

            <!-- Rationale annotation -->
            <div v-if="selectedVersion.rationale" class="mb-4 rounded-lg bg-surface-secondary border border-border px-4 py-3">
              <p class="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1">Rationale</p>
              <p class="text-sm text-text-secondary leading-6">{{ selectedVersion.rationale }}</p>
            </div>

            <!-- Model binding badge -->
            <div v-if="selectedVersion.model_pin" class="mb-4 flex items-center gap-2">
              <span class="text-xs text-text-muted">Model pin:</span>
              <ModelPinBadge :model-pin="selectedVersion.model_pin" :deprecated="isDeprecated(selectedVersion.model_pin, deprecatedModels)" />
            </div>

            <!-- Tags -->
            <div v-if="selectedVersion.tags && selectedVersion.tags.length > 0" class="mb-4 flex items-center gap-2 flex-wrap">
              <span
                v-for="tag in selectedVersion.tags"
                :key="tag"
                class="text-xs px-2 py-0.5 rounded-full bg-border text-text-secondary"
              >
                {{ tag }}
              </span>
            </div>

            <!-- Content block (monospace pre) -->
            <div class="rounded-xl border border-border bg-surface-secondary overflow-hidden">
              <div class="flex items-center justify-between px-4 py-2 border-b border-border bg-surface">
                <span class="text-xs font-mono text-text-muted">content</span>
                <span class="text-xs text-text-muted px-1.5 py-0.5 rounded bg-border font-mono">
                  {{ selectedVersion.content.split('\n').length }} line{{ selectedVersion.content.split('\n').length !== 1 ? 's' : '' }}
                </span>
              </div>
              <pre class="p-4 text-sm font-mono text-text-primary whitespace-pre-wrap break-words leading-6 overflow-x-auto max-h-96">{{ selectedVersion.content }}</pre>
            </div>

            <!-- Eval cases (eval_suite assets only) -->
            <div v-if="asset.asset_type === 'eval_suite'" class="mt-6">
              <h3 class="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
                Eval cases
                <span v-if="versionCases" class="text-text-muted font-normal normal-case tracking-tight ml-1">
                  ({{ versionCases.length }})
                </span>
              </h3>

              <div v-if="casesLoading && !versionCases" class="text-sm text-text-muted py-2">Loading cases…</div>

              <div v-else-if="versionCases && versionCases.length > 0" class="rounded-xl border border-border overflow-hidden">
                <table class="w-full text-xs">
                  <thead>
                    <tr class="border-b border-border bg-surface-secondary">
                      <th class="text-left px-3 py-2 text-text-muted font-medium w-8">#</th>
                      <th class="text-left px-3 py-2 text-text-muted font-medium">Input</th>
                      <th class="text-left px-3 py-2 text-text-muted font-medium">Expected</th>
                      <th class="text-left px-3 py-2 text-text-muted font-medium">Strategy</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(c, i) in versionCases" :key="c.id" class="border-b border-border last:border-0 align-top">
                      <td class="px-3 py-2 text-text-muted font-mono">{{ i + 1 }}</td>
                      <td class="px-3 py-2 text-text-primary whitespace-pre-wrap break-words">{{ c.input }}</td>
                      <td class="px-3 py-2 text-text-secondary whitespace-pre-wrap break-words">{{ c.expected_output }}</td>
                      <td class="px-3 py-2">
                        <span class="px-1.5 py-0.5 rounded bg-border text-text-secondary font-mono">{{ c.grading_strategy }}</span>
                        <span v-if="c.grading_config?.pattern" class="block mt-1 text-text-muted font-mono">/{{ c.grading_config.pattern }}/</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <p v-else class="text-xs text-text-muted">
                No eval cases on this version. Cases are immutable per version —
                <template v-if="isOwner">commit a <button class="text-accent hover:underline" @click="openNewVersion">new version</button> to add them.</template>
                <template v-else>the owner can commit a new version to add them.</template>
              </p>
            </div>
          </template>
        </main>
      </div>

      <!-- Add to board modal (KC-046) -->
      <div
        v-if="showAddToBoard"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
        @click.self="showAddToBoard = false"
      >
        <div class="bg-surface rounded-2xl shadow-xl p-6 w-full max-w-md">
          <h2 class="text-base font-semibold text-text-primary mb-1">Add to board</h2>
          <p class="text-xs text-text-muted mb-4">
            Projects v{{ selectedVersion?.version_num }} into the board's knowledge base as a prompt asset source.
          </p>

          <div class="space-y-3">
            <div>
              <label class="block text-xs font-medium text-text-secondary mb-1">Board</label>
              <p v-if="boardsLoading" class="text-xs text-text-muted">Loading boards…</p>
              <select
                v-else-if="myBoards.length > 0"
                v-model="abBoardId"
                class="w-full border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface focus:outline-none focus:border-accent"
              >
                <option v-for="b in myBoards" :key="b.id" :value="b.id">{{ b.title }}</option>
              </select>
              <p v-else class="text-xs text-text-muted">
                No boards yet.
                <NuxtLink to="/boards" class="text-accent hover:underline">Create one</NuxtLink> first.
              </p>
            </div>

            <div>
              <label class="block text-xs font-medium text-text-secondary mb-1">Lane (optional)</label>
              <input
                v-model="abLane"
                type="text"
                placeholder="e.g. Prompts"
                class="w-full border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
              />
            </div>

            <div>
              <label class="block text-xs font-medium text-text-secondary mb-1">Curator note (optional)</label>
              <input
                v-model="abNote"
                type="text"
                placeholder="Why this prompt belongs on the board"
                class="w-full border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
              />
            </div>
          </div>

          <p v-if="abError" class="text-xs text-warning mt-3">{{ abError }}</p>
          <p v-if="abSuccess" class="text-xs text-grounded mt-3">{{ abSuccess }}</p>

          <div class="flex gap-3 justify-end mt-5">
            <button
              class="px-4 py-2 rounded-lg text-sm text-text-muted hover:bg-surface-secondary transition-colors"
              @click="showAddToBoard = false"
            >
              {{ abSuccess ? 'Close' : 'Cancel' }}
            </button>
            <button
              :disabled="abSaving || !abBoardId || myBoards.length === 0"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
              @click="submitAddToBoard"
            >
              {{ abSaving ? 'Adding…' : 'Add to board' }}
            </button>
          </div>
        </div>
      </div>

      <!-- New version modal (KC-043) -->
      <div
        v-if="showNewVersion"
        class="fixed inset-0 z-50 flex items-start justify-center bg-black/50 backdrop-blur-sm pt-16 px-4 pb-4 overflow-y-auto"
        @click.self="showNewVersion = false"
      >
        <div class="bg-surface rounded-2xl shadow-2xl w-full max-w-3xl">
          <div class="flex items-center justify-between px-6 py-4 border-b border-border">
            <h2 class="text-sm font-semibold text-text-primary">New version</h2>
            <button class="text-text-muted hover:text-text-primary transition-colors" @click="showNewVersion = false">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="p-6 space-y-4">
            <div>
              <label class="block text-xs font-medium text-text-secondary mb-1">Content</label>
              <textarea
                v-model="nvContent"
                rows="6"
                class="w-full border border-border rounded-lg px-3 py-2 text-sm font-mono text-text-primary bg-surface focus:outline-none focus:border-accent resize-none"
              />
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-text-secondary mb-1">Rationale</label>
                <input
                  v-model="nvRationale"
                  type="text"
                  placeholder="Why this version exists"
                  class="w-full border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
                />
              </div>
              <div>
                <label class="block text-xs font-medium text-text-secondary mb-1">Model pin (optional)</label>
                <input
                  v-model="nvModelPin"
                  type="text"
                  placeholder="e.g. mistral:7b-instruct"
                  class="w-full border border-border rounded-lg px-3 py-2 text-sm font-mono text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
                />
              </div>
            </div>

            <!-- Eval case editor (eval_suite only) -->
            <div v-if="asset.asset_type === 'eval_suite'">
              <div class="flex items-center justify-between mb-2">
                <label class="text-xs font-medium text-text-secondary">
                  Eval cases
                  <span class="text-text-muted font-normal">— committed with this version, immutable afterwards</span>
                </label>
                <button
                  class="text-xs px-2 py-1 rounded-lg border border-border text-text-secondary hover:bg-surface-secondary transition-colors"
                  @click="addCaseRow"
                >
                  + Add case
                </button>
              </div>

              <p v-if="nvCases.length === 0" class="text-xs text-text-muted py-1">
                No cases yet — the eval worker will report 0/0 for this version.
              </p>

              <div v-else class="space-y-2">
                <div
                  v-for="(c, i) in nvCases"
                  :key="i"
                  class="rounded-lg border border-border p-3 space-y-2 bg-surface-secondary"
                >
                  <div class="flex items-center justify-between">
                    <span class="text-xs font-mono text-text-muted">case {{ i + 1 }}</span>
                    <button class="text-xs text-text-muted hover:text-warning transition-colors" @click="removeCaseRow(i)">
                      Remove
                    </button>
                  </div>
                  <textarea
                    v-model="c.input"
                    rows="2"
                    placeholder="Input prompt"
                    class="w-full border border-border rounded-lg px-3 py-2 text-xs font-mono text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent resize-none"
                  />
                  <div class="flex gap-2">
                    <input
                      v-model="c.expected_output"
                      type="text"
                      placeholder="Expected output"
                      class="flex-1 border border-border rounded-lg px-3 py-2 text-xs font-mono text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
                    />
                    <select
                      v-model="c.grading_strategy"
                      class="border border-border rounded-lg px-2 py-2 text-xs text-text-primary bg-surface focus:outline-none focus:border-accent"
                    >
                      <option v-for="s in GRADING_STRATEGIES" :key="s" :value="s">{{ s }}</option>
                    </select>
                  </div>
                  <input
                    v-if="c.grading_strategy === 'regex'"
                    v-model="c.pattern"
                    type="text"
                    placeholder="Regex pattern (falls back to expected output)"
                    class="w-full border border-border rounded-lg px-3 py-2 text-xs font-mono text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
                  />
                </div>
              </div>
            </div>

            <p v-if="nvError" class="text-xs text-warning">{{ nvError }}</p>

            <div class="flex gap-3 justify-end pt-2">
              <button
                class="px-4 py-2 rounded-lg text-sm text-text-muted hover:bg-surface-secondary transition-colors"
                @click="showNewVersion = false"
              >
                Cancel
              </button>
              <button
                :disabled="nvSaving || !nvContent.trim()"
                class="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
                @click="submitNewVersion"
              >
                {{ nvSaving ? 'Committing…' : 'Commit version' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Diff modal -->
      <div
        v-if="showDiff && diffFromVersion && diffToVersion"
        class="fixed inset-0 z-50 flex items-start justify-center bg-black/50 backdrop-blur-sm pt-16 px-4 pb-4 overflow-y-auto"
        @click.self="showDiff = false"
      >
        <div class="bg-surface rounded-2xl shadow-2xl w-full max-w-3xl">
          <div class="flex items-center justify-between px-6 py-4 border-b border-border">
            <h2 class="text-sm font-semibold text-text-primary">
              Diff: v{{ diffFromVersion.version_num }} → v{{ diffToVersion.version_num }}
            </h2>
            <button
              class="text-text-muted hover:text-text-primary transition-colors"
              @click="showDiff = false"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="p-6">
            <!-- Diff legend -->
            <div class="flex items-center gap-4 mb-4 text-xs">
              <span class="flex items-center gap-1.5">
                <span class="w-3 h-3 rounded-sm bg-grounded/20 border border-grounded/40 inline-block" />
                Added
              </span>
              <span class="flex items-center gap-1.5">
                <span class="w-3 h-3 rounded-sm bg-warning/20 border border-warning/40 inline-block" />
                Removed
              </span>
              <span class="flex items-center gap-1.5">
                <span class="w-3 h-3 rounded-sm bg-border inline-block" />
                Unchanged
              </span>
            </div>

            <div v-if="diffLines.length === 0" class="text-sm text-text-muted text-center py-8">
              Content is identical.
            </div>

            <div v-else class="rounded-xl border border-border overflow-hidden font-mono text-sm">
              <div
                v-for="(dl, idx) in diffLines"
                :key="idx"
                class="flex items-start px-4 py-0.5 leading-6"
                :class="{
                  'bg-grounded/10 text-grounded': dl.type === 'added',
                  'bg-warning/10 text-warning line-through': dl.type === 'removed',
                  'text-text-secondary': dl.type === 'unchanged',
                }"
              >
                <span class="w-4 shrink-0 text-xs opacity-60 select-none mr-3 mt-0.5">
                  {{ dl.type === 'added' ? '+' : dl.type === 'removed' ? '−' : ' ' }}
                </span>
                <span class="whitespace-pre-wrap break-words min-w-0">{{ dl.line || ' ' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
