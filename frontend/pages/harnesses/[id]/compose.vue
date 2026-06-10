<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

import { ref, computed, onMounted } from 'vue'

const route = useRoute()
const harnessId = route.params.id as string
const auth = useAuthStore()

// ── Types ─────────────────────────────────────────────────────────────────────

interface HarnessOwner { id: string; handle: string; display_name: string }

interface HarnessAssetSlot {
  id: string
  harness_id: string
  asset_version_id: string
  role: string
  position: number
  added_at: string
}

interface HarnessOut {
  id: string
  title: string
  description: string
  visibility: string
  fork_count: number
  forked_from_id: string | null
  fork_lineage: string[]
  created_at: string
  updated_at: string
  owner: HarnessOwner | null
  assets: HarnessAssetSlot[]
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
  versions: AssetVersion[]
}

interface EvalRunOut {
  id: string
  harness_id: string
  model_pin: string
  status: string
  metrics: {
    total: number
    passed: number
    failed: number
    pass_rate: number
    results: {
      case_id: string
      passed: boolean
      actual_output: string
      latency_ms: number
      grading_strategy: string
    }[]
  } | null
  created_at: string
  updated_at: string
}

// ── State ──────────────────────────────────────────────────────────────────────

const harness = ref<HarnessOut | null>(null)
const allAssets = ref<AssetOut[]>([])
const loading = ref(true)
const pageError = ref<string | null>(null)

// Version lookup map: version_id → {assetTitle, versionNum, modelPin, status}
const versionById = computed(() => {
  const m = new Map<string, { assetId: string; assetTitle: string; versionNum: number; modelPin: string | null; status: string }>()
  for (const a of allAssets.value) {
    for (const v of a.versions) {
      m.set(v.id, { assetId: a.id, assetTitle: a.title, versionNum: v.version_num, modelPin: v.model_pin, status: v.status })
    }
  }
  return m
})

// ── Add / Swap slot modal ───────────────────────────────────────────────────

const ROLES = [
  { value: 'system_prompt', label: 'System Prompt' },
  { value: 'eval_suite', label: 'Eval Suite' },
  { value: 'few_shot_set', label: 'Few-Shot Set' },
  { value: 'chain_spec', label: 'Chain Spec' },
  { value: 'tool_spec', label: 'Tool Spec' },
]

const showSlotModal = ref(false)
const slotModalMode = ref<'add' | 'swap'>('add')
const swapTargetSlotId = ref<string | null>(null)
const slotRole = ref('eval_suite')
const slotAssetId = ref('')
const slotVersionId = ref('')
const slotSaving = ref(false)
const slotError = ref<string | null>(null)

const selectedAssetVersions = computed(() => {
  const a = allAssets.value.find(x => x.id === slotAssetId.value)
  return a?.versions ?? []
})

function openAddSlot() {
  slotModalMode.value = 'add'
  slotRole.value = 'eval_suite'
  slotAssetId.value = ''
  slotVersionId.value = ''
  slotError.value = null
  swapTargetSlotId.value = null
  showSlotModal.value = true
}

function openSwapSlot(slot: HarnessAssetSlot) {
  slotModalMode.value = 'swap'
  slotRole.value = slot.role
  // Pre-select the current asset/version if known
  const meta = versionById.value.get(slot.asset_version_id)
  slotAssetId.value = meta?.assetId ?? ''
  slotVersionId.value = slot.asset_version_id
  slotError.value = null
  swapTargetSlotId.value = slot.id
  showSlotModal.value = true
}

async function saveSlot() {
  if (!slotVersionId.value || slotSaving.value) return
  slotSaving.value = true
  slotError.value = null
  try {
    if (slotModalMode.value === 'add') {
      const slot = await $fetch<HarnessAssetSlot>(`/api/harnesses/${harnessId}/assets`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${auth.token}` },
        body: { asset_version_id: slotVersionId.value, role: slotRole.value, position: 0 },
      })
      harness.value?.assets.push(slot)
    } else {
      const slot = await $fetch<HarnessAssetSlot>(`/api/harnesses/${harnessId}/assets/${slotRole.value}`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${auth.token}` },
        body: { new_asset_version_id: slotVersionId.value },
      })
      if (harness.value) {
        harness.value.assets = harness.value.assets.map(s =>
          s.role === slot.role ? { ...s, asset_version_id: slot.asset_version_id } : s
        )
      }
    }
    showSlotModal.value = false
  } catch (err: unknown) {
    slotError.value = err instanceof Error ? err.message : 'Failed to save slot'
  } finally {
    slotSaving.value = false
  }
}

// ── Fork dialog ────────────────────────────────────────────────────────────

const showFork = ref(false)
const forkTitle = ref('')
const forking = ref(false)
const forkError = ref<string | null>(null)

function openFork() {
  forkTitle.value = harness.value ? `${harness.value.title} [fork]` : ''
  forkError.value = null
  showFork.value = true
}

async function forkHarness() {
  if (!forkTitle.value.trim() || forking.value) return
  forking.value = true
  forkError.value = null
  try {
    const result = await $fetch<{ id: string }>(`/api/harnesses/${harnessId}/fork`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { new_title: forkTitle.value.trim(), visibility: 'private' },
    })
    showFork.value = false
    await navigateTo(`/harnesses/${result.id}/compose`)
  } catch (err: unknown) {
    forkError.value = err instanceof Error ? err.message : 'Fork failed'
  } finally {
    forking.value = false
  }
}

// ── Eval panel ─────────────────────────────────────────────────────────────

const availableModels = ref<string[]>([])
const selectedModel = ref('')
const evalSubmitting = ref(false)
const evalError = ref<string | null>(null)
const evalRunId = ref<string | null>(null)
const evalStatus = ref('')
const evalProgress = ref({ current: 0, total: 0, passedSoFar: 0 })
const evalMetrics = ref<EvalRunOut['metrics']>(null)
const evalCaseResults = ref<NonNullable<EvalRunOut['metrics']>['results']>([])

const hasEvalSuiteSlot = computed(() =>
  harness.value?.assets.some(s => s.role === 'eval_suite') ?? false
)

const evalProgressPct = computed(() =>
  evalProgress.value.total > 0
    ? Math.round((evalProgress.value.current / evalProgress.value.total) * 100)
    : 0
)

async function submitEval() {
  if (!hasEvalSuiteSlot.value || !selectedModel.value || evalSubmitting.value) return
  evalSubmitting.value = true
  evalError.value = null
  evalMetrics.value = null
  evalCaseResults.value = []
  evalProgress.value = { current: 0, total: 0, passedSoFar: 0 }
  evalRunId.value = null
  evalStatus.value = 'queued'

  try {
    const run = await $fetch<EvalRunOut>(`/api/harnesses/${harnessId}/eval`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { model: selectedModel.value },
    })
    evalRunId.value = run.id
    evalStatus.value = run.status
    await streamEvalEvents(run.id)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Failed to submit eval'
    // Distinguish 422 (model not available) from 503 (Ollama unreachable)
    if (msg.includes('503') || msg.includes('reach Ollama')) {
      evalError.value = 'Ollama is not reachable. Make sure the Ollama service is running.'
    } else if (msg.includes('422') || msg.includes('not available')) {
      evalError.value = `Model not available locally. Choose a model from the list above.`
    } else {
      evalError.value = msg
    }
    evalStatus.value = 'failed'
  } finally {
    evalSubmitting.value = false
  }
}

async function streamEvalEvents(runId: string) {
  try {
    const res = await fetch(`/api/harnesses/${harnessId}/eval/${runId}/events`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    if (!res.ok || !res.body) {
      evalError.value = 'Could not connect to eval event stream'
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() ?? ''

      for (const rawEvent of chunks) {
        if (!rawEvent.trim()) continue
        const dataLine = rawEvent.split('\n').find(l => l.startsWith('data:'))
        if (!dataLine) continue
        const raw = dataLine.slice('data:'.length)
        const data = raw.startsWith(' ') ? raw.slice(1) : raw
        if (!data) continue

        try {
          const evt = JSON.parse(data)
          if (evt.type === 'case') {
            evalStatus.value = 'running'
            evalProgress.value = {
              current: evt.case_num,
              total: evt.total,
              passedSoFar: evalProgress.value.passedSoFar + (evt.passed ? 1 : 0),
            }
            evalCaseResults.value.push({
              case_id: `Case ${evt.case_num}`,
              passed: evt.passed,
              actual_output: '',
              latency_ms: evt.latency_ms,
              grading_strategy: '',
            })
          } else if (evt.type === 'complete') {
            evalStatus.value = 'completed'
            if (evt.metrics) {
              evalMetrics.value = { ...evt.metrics, failed: evt.metrics.total - evt.metrics.passed, results: evalCaseResults.value }
            }
            // Fetch full run for per-case actual_output
            await fetchFinalEvalRun(runId)
          } else if (evt.type === 'error') {
            evalStatus.value = 'failed'
            evalError.value = evt.message || 'Eval job failed — check worker logs'
          }
        } catch {
          // malformed event — skip
        }
      }
    }
  } catch {
    evalError.value = 'Lost connection to eval event stream'
    evalStatus.value = 'failed'
  }
}

async function fetchFinalEvalRun(runId: string) {
  try {
    const run = await $fetch<EvalRunOut>(`/api/harnesses/${harnessId}/eval/${runId}`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    evalStatus.value = run.status
    if (run.metrics) {
      evalMetrics.value = run.metrics
      evalCaseResults.value = run.metrics.results ?? []
    }
  } catch {
    // best effort — SSE results already populated
  }
}

// ── Role display helpers ───────────────────────────────────────────────────

const roleLabel: Record<string, string> = {
  system_prompt: 'System Prompt',
  eval_suite: 'Eval Suite',
  few_shot_set: 'Few-Shot Set',
  chain_spec: 'Chain Spec',
  tool_spec: 'Tool Spec',
}

const roleColor: Record<string, string> = {
  system_prompt: 'text-accent bg-accent/10',
  eval_suite: 'text-warning bg-warning/10',
  few_shot_set: 'text-grounded bg-grounded/10',
  chain_spec: 'text-text-secondary bg-border',
  tool_spec: 'text-text-secondary bg-border',
}

const visibilityColor: Record<string, string> = {
  private: 'text-text-muted bg-border',
  team: 'text-accent bg-accent/10',
  public: 'text-grounded bg-grounded/10',
}

// ── Load ───────────────────────────────────────────────────────────────────

async function loadPage() {
  loading.value = true
  pageError.value = null
  try {
    const [h, assets, modelsRes] = await Promise.all([
      $fetch<HarnessOut>(`/api/harnesses/${harnessId}`, {
        headers: { Authorization: `Bearer ${auth.token}` },
      }),
      $fetch<{ id: string; title: string; description: string; asset_type: string; visibility: string; fork_count: number; versions?: AssetVersion[] }[]>(
        '/api/assets',
        { headers: { Authorization: `Bearer ${auth.token}` } }
      ),
      $fetch<{ models: string[] }>('/api/models'),
    ])

    harness.value = h as HarnessOut

    // Fetch full asset details (with versions) in parallel
    const assetDetails = await Promise.all(
      assets.map(a =>
        $fetch<AssetOut>(`/api/assets/${a.id}`, {
          headers: { Authorization: `Bearer ${auth.token}` },
        }).catch(() => null)
      )
    )
    allAssets.value = assetDetails.filter(Boolean) as AssetOut[]

    availableModels.value = modelsRes.models
    if (modelsRes.models.length > 0) selectedModel.value = modelsRes.models[0]
  } catch {
    pageError.value = 'Harness not found or you do not have access.'
  } finally {
    loading.value = false
  }
}

onMounted(loadPage)
</script>

<template>
  <div class="min-h-screen bg-surface">
    <div v-if="loading" class="flex items-center justify-center py-32">
      <div class="text-sm text-text-muted">Loading…</div>
    </div>

    <div v-else-if="pageError" class="text-center py-20 text-warning text-sm">
      {{ pageError }}
    </div>

    <template v-else-if="harness">
      <!-- Header -->
      <div class="border-b border-border bg-surface">
        <div class="max-w-5xl mx-auto px-6 py-8">
          <div class="flex items-start gap-4">
            <div class="flex-1 min-w-0">
              <div class="mb-2">
                <NuxtLink to="/harnesses" class="text-xs text-text-muted hover:text-accent transition-colors">
                  ← Harnesses
                </NuxtLink>
              </div>
              <h1 class="text-2xl font-semibold text-text-primary mb-2">{{ harness.title }}</h1>
              <p v-if="harness.description" class="text-sm text-text-secondary leading-6 max-w-2xl mb-3">
                {{ harness.description }}
              </p>
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="visibilityColor[harness.visibility]">
                  {{ harness.visibility }}
                </span>
                <span class="text-xs text-text-muted">{{ harness.assets.length }} slot{{ harness.assets.length !== 1 ? 's' : '' }}</span>
                <span v-if="harness.fork_count > 0" class="text-xs text-text-muted">
                  · {{ harness.fork_count }} fork{{ harness.fork_count !== 1 ? 's' : '' }}
                </span>
                <span v-if="harness.owner" class="text-xs text-text-muted">
                  · by @{{ harness.owner.handle }}
                </span>
              </div>
            </div>

            <ClientOnly>
              <button
                class="shrink-0 flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-border text-text-secondary hover:bg-surface-secondary transition-colors"
                @click="openFork"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
                Fork
              </button>
            </ClientOnly>
          </div>
        </div>
      </div>

      <!-- Body -->
      <div class="max-w-5xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-2 gap-8">

        <!-- Asset Slots panel -->
        <section>
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-xs font-semibold text-text-secondary uppercase tracking-wider">Asset Slots</h2>
            <ClientOnly>
              <button
                class="text-xs px-3 py-1.5 rounded-lg border border-border text-text-secondary hover:bg-surface-secondary transition-colors"
                @click="openAddSlot"
              >
                + Add slot
              </button>
            </ClientOnly>
          </div>

          <div v-if="harness.assets.length === 0" class="rounded-xl border border-border bg-surface p-6 text-center text-sm text-text-muted">
            No slots yet.
            <button class="block mt-1 text-accent hover:underline mx-auto text-xs" @click="openAddSlot">Add the first slot</button>
          </div>

          <ul v-else class="space-y-2">
            <li
              v-for="slot in harness.assets"
              :key="slot.id"
              class="rounded-xl border border-border bg-surface p-4"
            >
              <div class="flex items-start gap-3">
                <div class="flex-1 min-w-0">
                  <span
                    class="inline-block text-xs px-2 py-0.5 rounded-full font-medium mb-1.5"
                    :class="roleColor[slot.role] ?? 'text-text-muted bg-border'"
                  >
                    {{ roleLabel[slot.role] ?? slot.role }}
                  </span>

                  <template v-if="versionById.get(slot.asset_version_id)">
                    <p class="text-sm font-medium text-text-primary truncate">
                      {{ versionById.get(slot.asset_version_id)!.assetTitle }}
                      <span class="text-text-muted font-normal ml-1">v{{ versionById.get(slot.asset_version_id)!.versionNum }}</span>
                    </p>
                    <div class="flex items-center gap-2 mt-0.5">
                      <span
                        class="text-xs px-1.5 py-0.5 rounded-full font-medium"
                        :class="versionById.get(slot.asset_version_id)!.status === 'active'
                          ? 'text-grounded bg-grounded/10'
                          : versionById.get(slot.asset_version_id)!.status === 'deprecated'
                            ? 'text-warning bg-warning/10'
                            : 'text-text-muted bg-border'"
                      >
                        {{ versionById.get(slot.asset_version_id)!.status }}
                      </span>
                      <span v-if="versionById.get(slot.asset_version_id)!.modelPin" class="text-xs font-mono text-text-muted">
                        {{ versionById.get(slot.asset_version_id)!.modelPin }}
                      </span>
                    </div>
                  </template>

                  <p v-else class="text-xs font-mono text-text-muted mt-0.5">
                    {{ slot.asset_version_id.slice(0, 8) }}…
                  </p>
                </div>

                <ClientOnly>
                  <button
                    class="shrink-0 text-xs px-2.5 py-1 rounded-lg border border-border text-text-muted hover:bg-surface-secondary transition-colors"
                    @click="openSwapSlot(slot)"
                  >
                    Swap
                  </button>
                </ClientOnly>
              </div>
            </li>
          </ul>

          <p v-if="!hasEvalSuiteSlot && harness.assets.length > 0" class="mt-3 text-xs text-warning">
            Add an <strong>Eval Suite</strong> slot to enable eval runs.
          </p>
        </section>

        <!-- Eval panel -->
        <section>
          <h2 class="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">Eval Run</h2>

          <div class="rounded-xl border border-border bg-surface p-5 space-y-4">
            <!-- Model selector -->
            <div>
              <label class="block text-xs font-medium text-text-secondary mb-1.5">Ollama model</label>
              <select
                v-if="availableModels.length > 0"
                v-model="selectedModel"
                class="w-full border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface focus:outline-none focus:border-accent"
              >
                <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
              </select>
              <p v-else class="text-xs text-text-muted">No local Ollama models found. Run <code class="font-mono bg-border px-1 rounded">docker compose run --rm ollama-init</code> to pull models.</p>
            </div>

            <!-- Run button -->
            <div>
              <button
                :disabled="!hasEvalSuiteSlot || !selectedModel || evalSubmitting || evalStatus === 'running'"
                class="w-full py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
                @click="submitEval"
              >
                <span v-if="evalSubmitting || evalStatus === 'running'">Running eval…</span>
                <span v-else>Run eval</span>
              </button>

              <p v-if="!hasEvalSuiteSlot" class="text-xs text-text-muted mt-1.5">
                Requires an <strong>Eval Suite</strong> slot to be configured.
              </p>
            </div>

            <!-- Progress bar -->
            <div v-if="evalStatus === 'running' || (evalStatus === 'completed' && evalProgress.total > 0)">
              <div class="flex items-center justify-between text-xs text-text-muted mb-1">
                <span>{{ evalProgress.current }} / {{ evalProgress.total }} cases</span>
                <span>{{ evalProgressPct }}%</span>
              </div>
              <div class="h-2 rounded-full bg-border overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-300"
                  :class="evalStatus === 'completed' ? 'bg-grounded' : 'bg-accent'"
                  :style="{ width: `${evalProgressPct}%` }"
                />
              </div>
            </div>

            <!-- Error -->
            <p v-if="evalError" class="text-xs text-warning">{{ evalError }}</p>

            <!-- Results summary -->
            <div v-if="evalMetrics" class="space-y-3">
              <div class="rounded-lg bg-surface-secondary border border-border px-4 py-3">
                <p class="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Result</p>
                <div class="flex items-end gap-3">
                  <span class="text-3xl font-semibold" :class="evalMetrics.pass_rate >= 0.8 ? 'text-grounded' : evalMetrics.pass_rate >= 0.5 ? 'text-warning' : 'text-red-500'">
                    {{ Math.round(evalMetrics.pass_rate * 100) }}%
                  </span>
                  <span class="text-sm text-text-muted mb-0.5">
                    {{ evalMetrics.passed }} / {{ evalMetrics.total }} passed
                  </span>
                </div>
              </div>

              <!-- Per-case table -->
              <div v-if="evalCaseResults.length > 0" class="rounded-lg border border-border overflow-hidden">
                <table class="w-full text-xs">
                  <thead>
                    <tr class="border-b border-border bg-surface-secondary">
                      <th class="text-left px-3 py-2 text-text-muted font-medium">Case</th>
                      <th class="text-left px-3 py-2 text-text-muted font-medium">Result</th>
                      <th class="text-right px-3 py-2 text-text-muted font-medium">Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(r, i) in evalCaseResults"
                      :key="i"
                      class="border-b border-border last:border-0"
                    >
                      <td class="px-3 py-2 font-mono text-text-muted">{{ r.case_id }}</td>
                      <td class="px-3 py-2">
                        <span
                          class="font-medium"
                          :class="r.passed ? 'text-grounded' : 'text-red-500'"
                        >
                          {{ r.passed ? 'PASS' : 'FAIL' }}
                        </span>
                      </td>
                      <td class="px-3 py-2 text-right text-text-muted">{{ r.latency_ms }}ms</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <p v-else-if="evalMetrics.total === 0" class="text-xs text-text-muted">
                No eval cases found on this harness's eval_suite version. Eval cases are seeded directly on the asset version — no UI editor is available yet.
              </p>
            </div>
          </div>
        </section>
      </div>

      <!-- Add / Swap slot modal -->
      <div
        v-if="showSlotModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
        @click.self="showSlotModal = false"
      >
        <div class="bg-surface rounded-2xl shadow-xl p-6 w-full max-w-md">
          <h2 class="text-base font-semibold text-text-primary mb-4">
            {{ slotModalMode === 'add' ? 'Add slot' : 'Swap slot version' }}
          </h2>

          <div class="space-y-3">
            <!-- Role -->
            <div>
              <label class="block text-xs font-medium text-text-secondary mb-1">Role</label>
              <select
                v-model="slotRole"
                :disabled="slotModalMode === 'swap'"
                class="w-full border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface focus:outline-none focus:border-accent disabled:opacity-60"
              >
                <option v-for="r in ROLES" :key="r.value" :value="r.value">{{ r.label }}</option>
              </select>
              <p v-if="slotModalMode === 'swap'" class="text-xs text-text-muted mt-1">Role cannot be changed when swapping. Remove the slot and re-add to change role.</p>
            </div>

            <!-- Asset -->
            <div>
              <label class="block text-xs font-medium text-text-secondary mb-1">Asset</label>
              <select
                v-model="slotAssetId"
                class="w-full border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface focus:outline-none focus:border-accent"
                @change="slotVersionId = ''"
              >
                <option value="">Select an asset…</option>
                <option v-for="a in allAssets" :key="a.id" :value="a.id">
                  {{ a.title }} ({{ a.asset_type.replace('_', ' ') }})
                </option>
              </select>
              <p v-if="allAssets.length === 0" class="text-xs text-text-muted mt-1">
                No assets found.
                <NuxtLink to="/assets" class="text-accent hover:underline">Create one</NuxtLink> first.
              </p>
            </div>

            <!-- Version -->
            <div v-if="slotAssetId">
              <label class="block text-xs font-medium text-text-secondary mb-1">Version</label>
              <select
                v-model="slotVersionId"
                class="w-full border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface focus:outline-none focus:border-accent"
              >
                <option value="">Select a version…</option>
                <option
                  v-for="v in selectedAssetVersions"
                  :key="v.id"
                  :value="v.id"
                >
                  v{{ v.version_num }} — {{ v.status }}{{ v.model_pin ? ` (${v.model_pin})` : '' }}{{ v.rationale ? ` · ${v.rationale.slice(0, 40)}` : '' }}
                </option>
              </select>
            </div>
          </div>

          <p v-if="slotError" class="text-xs text-warning mt-3">{{ slotError }}</p>

          <div class="flex gap-3 justify-end mt-5">
            <button
              class="px-4 py-2 rounded-lg text-sm text-text-muted hover:bg-surface-secondary transition-colors"
              @click="showSlotModal = false"
            >
              Cancel
            </button>
            <button
              :disabled="!slotVersionId || slotSaving"
              class="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
              @click="saveSlot"
            >
              {{ slotSaving ? 'Saving…' : slotModalMode === 'add' ? 'Add slot' : 'Swap version' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Fork dialog -->
      <div
        v-if="showFork"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
        @click.self="showFork = false"
      >
        <div class="bg-surface rounded-2xl shadow-xl p-6 w-full max-w-md">
          <h2 class="text-base font-semibold text-text-primary mb-1">Fork this harness</h2>
          <p class="text-xs text-text-muted mb-4">
            Creates a private copy with all {{ harness.assets.length }} slot{{ harness.assets.length !== 1 ? 's' : '' }} preserved.
          </p>
          <input
            v-model="forkTitle"
            type="text"
            placeholder="Name for your fork"
            class="w-full border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent mb-3"
            @keydown.enter="forkHarness"
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
              @click="forkHarness"
            >
              {{ forking ? 'Forking…' : 'Fork' }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
