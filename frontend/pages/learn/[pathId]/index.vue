<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAuthStore } from '~/stores/auth'
import { videoDeepLink } from '~/utils/video'

const route = useRoute()
const pathId = route.params.pathId as string
const auth = useAuthStore()

let _pollTimer: ReturnType<typeof setInterval> | null = null

function _clearPoll() {
  if (_pollTimer !== null) {
    clearInterval(_pollTimer)
    _pollTimer = null
  }
}

interface Distractor {
  id: string
  text: string
  why_wrong_passage_id: string
  misconception_label: string | null
}

interface Choice {
  id: string
  text: string
}

interface AssessmentItem {
  id: string
  question_text: string
  correct_answer: string | null
  grounding_passage_id: string
  distractors: Distractor[]
  choices: Choice[]
}

interface SourcePassage {
  chunk_id: string
  locator: string
  source_id: string
  excerpt: string
}

interface ConceptGate {
  mastered: boolean
  correct_items: number
  item_count: number
}

interface PathConcept {
  id: string
  position: number
  title: string
  explanation_text: string
  explanation_passage_ids: string[]
  source_passages: SourcePassage[]
  instructor_annotation: string | null
  status: string
  assessment_items: AssessmentItem[]
  locked: boolean
  gate: ConceptGate | null
}

interface LearningPath {
  id: string
  kb_id: string
  learning_goal: string
  status: string
  version: number
  mastery_mode: string
  mastery_threshold: number
  concepts: PathConcept[]
  learned_concept_ids: string[]
  owner: { id: string; handle: string; display_name: string } | null
}

interface AttemptResult {
  correct: boolean
  correct_answer: string | null
  grounding_passage_id: string
  feedback: string | null
}

const path = ref<LearningPath | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Per-concept UI state
const activeConcept = ref<number>(0)
const selectedAnswer = ref<Record<string, string>>({})     // itemId → chosen text
const attemptResults = ref<Record<string, AttemptResult>>({}) // itemId → result
const submitting = ref<Record<string, boolean>>({})

// Instructor panel
const showPassages = ref<Record<string, boolean>>({})

// ── Private notes (KC-047) ──────────────────────────────────────────────────

const noteBodies = ref<Record<string, string>>({})
const noteLoaded = ref<Record<string, boolean>>({})
const noteSaving = ref<Record<string, boolean>>({})
const noteSaved = ref<Record<string, boolean>>({})

async function loadNote(conceptId: string) {
  if (noteLoaded.value[conceptId]) return
  noteLoaded.value[conceptId] = true
  try {
    const note = await $fetch<{ body: string } | null>(
      `/api/learning-paths/${pathId}/concepts/${conceptId}/note`,
      { headers: { Authorization: `Bearer ${auth.token}` } },
    )
    if (note?.body) noteBodies.value[conceptId] = note.body
  } catch {
    noteLoaded.value[conceptId] = false
  }
}

async function saveNote(conceptId: string) {
  if (noteSaving.value[conceptId]) return
  noteSaving.value[conceptId] = true
  try {
    await $fetch(`/api/learning-paths/${pathId}/concepts/${conceptId}/note`, {
      method: 'PUT',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { body: noteBodies.value[conceptId] ?? '' },
    })
    noteSaved.value[conceptId] = true
    setTimeout(() => { noteSaved.value[conceptId] = false }, 2000)
  } catch {
    // keep the draft in the textarea; the user can retry
  } finally {
    noteSaving.value[conceptId] = false
  }
}

watch(
  () => path.value?.concepts[activeConcept.value]?.id,
  (id) => { if (id) loadNote(id) },
  { immediate: true },
)

// ── Learner progress (KC-048) ───────────────────────────────────────────────

const isOwner = computed(() =>
  auth.isLoggedIn && path.value?.owner?.id === auth.user?.id
)

const learnedIds = ref<Set<string>>(new Set())
const learnedSaving = ref<Record<string, boolean>>({})

watch(
  () => path.value?.learned_concept_ids,
  (ids) => { if (ids) learnedIds.value = new Set(ids) },
  { immediate: true },
)

async function toggleLearned(conceptId: string) {
  if (learnedSaving.value[conceptId]) return
  const wasLearned = learnedIds.value.has(conceptId)
  learnedSaving.value[conceptId] = true
  try {
    await $fetch(`/api/learning-paths/${pathId}/concepts/${conceptId}/learned`, {
      method: wasLearned ? 'DELETE' : 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    const next = new Set(learnedIds.value)
    if (wasLearned) next.delete(conceptId)
    else next.add(conceptId)
    learnedIds.value = next
    refreshGates()
  } catch {
    // leave state unchanged; the user can retry
  } finally {
    learnedSaving.value[conceptId] = false
  }
}

// Source type/url per source_id — resolves video passages to deep links (KC-094)
const sourceInfo = ref<Record<string, { type: string; raw_url: string | null }>>({})

async function loadSourceInfo(kbId: string) {
  if (Object.keys(sourceInfo.value).length > 0) return
  try {
    const sources = await $fetch<{ id: string; type: string; raw_url: string | null }[]>(
      `/api/kb/${kbId}/sources`,
      { headers: { Authorization: `Bearer ${auth.token}` } },
    )
    sourceInfo.value = Object.fromEntries(sources.map(s => [s.id, { type: s.type, raw_url: s.raw_url }]))
  } catch {
    // deep links degrade to plain locators
  }
}

function passageDeepLink(p: SourcePassage): string | null {
  const info = sourceInfo.value[p.source_id]
  if (!info || info.type !== 'video') return null
  return videoDeepLink(info.raw_url, p.locator)
}

async function fetchPath() {
  loading.value = true
  try {
    const data = await $fetch<LearningPath>(`/api/learning-paths/${pathId}`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    path.value = data
    loadSourceInfo(data.kb_id)
    if (data.status === 'generating') {
      _startPolling()
    } else {
      _clearPoll()
    }
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to load learning path'
  } finally {
    loading.value = false
  }
}

async function _pollPath() {
  try {
    const data = await $fetch<LearningPath>(`/api/learning-paths/${pathId}`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    path.value = data
    if (data.status !== 'generating') {
      _clearPoll()
    }
  } catch {
    // keep polling — transient error
  }
}

function _startPolling() {
  _clearPoll()
  _pollTimer = setInterval(_pollPath, 4000)
}

async function submitAnswer(concept: PathConcept, item: AssessmentItem) {
  const answer = selectedAnswer.value[item.id]
  if (!answer || submitting.value[item.id]) return
  submitting.value[item.id] = true
  try {
    const result = await $fetch<AttemptResult>(
      `/api/learning-paths/${pathId}/concepts/${concept.id}/items/${item.id}/attempt`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${auth.token}` },
        body: { answer },
      }
    )
    attemptResults.value[item.id] = result
    if (result.correct) refreshGates()
  } catch {
    // keep selected, let user retry
  } finally {
    submitting.value[item.id] = false
  }
}

async function publishPath() {
  if (!path.value) return
  await $fetch<unknown>(`/api/learning-paths/${pathId}/publish`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${auth.token}` },
  })
  if (path.value) path.value.status = 'published'
}

async function updateConceptStatus(concept: PathConcept, newStatus: 'accepted' | 'pruned') {
  await $fetch<unknown>(`/api/learning-paths/${pathId}/concepts/${concept.id}`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${auth.token}` },
    body: { status: newStatus },
  })
  concept.status = newStatus
}

const acceptedCount = computed(() =>
  path.value?.concepts.filter(c => c.status === 'accepted').length ?? 0
)
const conceptCount = computed(() => path.value?.concepts.length ?? 0)

// ── Mastery gates (KC-089, docs/14) ─────────────────────────────────────────

const gateMode = ref<'off' | 'soft' | 'hard'>('off')
const gateThresholdPct = ref(80)
const gateSaving = ref(false)

watch(
  () => path.value && [path.value.mastery_mode, path.value.mastery_threshold] as const,
  (v) => {
    if (!v) return
    gateMode.value = v[0] as 'off' | 'soft' | 'hard'
    gateThresholdPct.value = Math.round((v[1] as number) * 100)
  },
  { immediate: true },
)

async function saveGateSettings() {
  if (gateSaving.value || !path.value) return
  const threshold = Math.min(100, Math.max(1, gateThresholdPct.value || 80)) / 100
  gateSaving.value = true
  try {
    await $fetch(`/api/learning-paths/${pathId}` as string, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { mastery_mode: gateMode.value, mastery_threshold: threshold },
    })
    path.value.mastery_mode = gateMode.value
    path.value.mastery_threshold = threshold
  } catch {
    // revert the selectors to what the server still has
    gateMode.value = path.value.mastery_mode as 'off' | 'soft' | 'hard'
    gateThresholdPct.value = Math.round(path.value.mastery_threshold * 100)
  } finally {
    gateSaving.value = false
  }
}

function isHardLocked(concept: PathConcept): boolean {
  return concept.locked && path.value?.mastery_mode === 'hard'
}

/** What the learner still has to do on the first unmastered predecessor. */
function unlockHint(idx: number): string | null {
  if (!path.value) return null
  for (let i = 0; i < idx; i++) {
    const c = path.value.concepts[i]
    if (c.status === 'pruned' || !c.gate || c.gate.mastered) continue
    if (c.gate.item_count > 0) {
      const needed = Math.ceil(path.value.mastery_threshold * c.gate.item_count) - c.gate.correct_items
      return `Answer ${needed} more assessment item${needed !== 1 ? 's' : ''} correctly in “${c.title}”.`
    }
    return `Mark “${c.title}” as learned.`
  }
  return null
}

/** Gate state is computed fresh per request — refetch quietly after any
 *  action that can change mastery, so locks open without a manual reload. */
function refreshGates() {
  if (path.value && path.value.mastery_mode !== 'off' && !isOwner.value) _pollPath()
}

// ── Owner analytics (KC-085, docs/13) ───────────────────────────────────────

interface LearnerAnalytics {
  user: { id: string; handle: string; display_name: string }
  learned_count: number
  completion_pct: number
  attempt_count: number
  correct_count: number
  correct_rate: number
  last_activity: string | null
}

interface ConceptAnalytics {
  concept_id: string
  title: string
  position: number
  learners_learned: number
  attempt_count: number
  correct_rate: number
  top_wrong_answers: { answer_text: string; count: number; misconception_label: string | null }[]
}

interface PathAnalytics {
  path_id: string
  active_concept_count: number
  learner_count: number
  learners: LearnerAnalytics[]
  concepts: ConceptAnalytics[]
}

const showAnalytics = ref(false)
const analytics = ref<PathAnalytics | null>(null)
const analyticsLoading = ref(false)
const analyticsError = ref<string | null>(null)

async function toggleAnalytics() {
  showAnalytics.value = !showAnalytics.value
  if (!showAnalytics.value || analyticsLoading.value) return
  analyticsLoading.value = true
  analyticsError.value = null
  try {
    analytics.value = await $fetch<PathAnalytics>(`/api/learning-paths/${pathId}/analytics`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
  } catch {
    analyticsError.value = 'Could not load analytics.'
  } finally {
    analyticsLoading.value = false
  }
}

function fmtDateTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—'
}

function highlightCitations(text: string): string {
  // Match both [SOURCE:uuid] (ideal) and bare [uuid] (model sometimes omits prefix)
  return text
    .replace(/\[SOURCE:([a-f0-9-]{36})\]/g, '<sup class="text-grounded font-mono text-xs">[src]</sup>')
    .replace(/\[([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\]/g, '<sup class="text-grounded font-mono text-xs">[src]</sup>')
}

onMounted(fetchPath)
onUnmounted(_clearPoll)
</script>

<template>
  <div class="min-h-screen bg-surface">
    <div v-if="loading" class="flex items-center justify-center h-64">
      <div class="text-text-muted text-sm animate-pulse">Loading learning path…</div>
    </div>

    <p v-else-if="error" class="text-center text-warning py-16 text-sm">{{ error }}</p>

    <template v-else-if="path">
      <!-- Top bar -->
      <div class="border-b border-border bg-surface sticky top-0 z-10">
        <div class="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <NuxtLink
            :to="`/kb/${path.kb_id}/learn`"
            class="text-xs text-text-muted hover:text-accent flex items-center gap-1"
          >
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
            Learning paths
          </NuxtLink>
          <div class="flex-1 min-w-0">
            <h1 class="text-sm font-semibold text-text-primary truncate">{{ path.learning_goal }}</h1>
          </div>
          <span
            v-if="path.status === 'generating'"
            class="text-xs text-text-muted bg-border px-2 py-0.5 rounded-full animate-pulse"
          >
            Generating…
          </span>
          <span
            v-else-if="path.status === 'failed'"
            class="text-xs text-warning bg-warning/10 px-2 py-0.5 rounded-full"
          >
            Generation failed
          </span>
          <span
            v-else-if="path.status === 'draft'"
            class="text-xs text-warning bg-warning/10 px-2 py-0.5 rounded-full"
          >
            Draft · {{ acceptedCount }}/{{ conceptCount }} accepted
          </span>
          <span
            v-else
            class="text-xs text-grounded bg-grounded/10 px-2 py-0.5 rounded-full"
          >
            Published
          </span>
          <div v-if="isOwner && path.status !== 'generating'" class="flex items-center gap-1.5">
            <label class="text-xs text-text-muted">Gates</label>
            <select
              v-model="gateMode"
              :disabled="gateSaving"
              class="text-xs border border-border rounded-lg px-2 py-1.5 bg-surface text-text-secondary focus:outline-none focus:border-accent disabled:opacity-50"
              @change="saveGateSettings"
            >
              <option value="off">Off</option>
              <option value="soft">Soft</option>
              <option value="hard">Hard</option>
            </select>
            <template v-if="gateMode !== 'off'">
              <input
                v-model.number="gateThresholdPct"
                type="number"
                min="1"
                max="100"
                :disabled="gateSaving"
                class="w-14 text-xs border border-border rounded-lg px-2 py-1.5 bg-surface text-text-secondary focus:outline-none focus:border-accent disabled:opacity-50"
                @change="saveGateSettings"
              />
              <span class="text-xs text-text-muted">%</span>
            </template>
          </div>
          <button
            v-if="isOwner && path.status !== 'generating'"
            class="text-xs px-3 py-1.5 rounded-lg border transition-colors"
            :class="showAnalytics ? 'border-accent text-accent bg-accent/5' : 'border-border text-text-secondary hover:bg-surface-secondary'"
            @click="toggleAnalytics"
          >
            Learners
          </button>
          <button
            v-if="isOwner && path.status === 'draft'"
            class="text-xs px-3 py-1.5 rounded-lg bg-grounded text-white hover:bg-green-700 transition-colors"
            @click="publishPath"
          >
            Publish
          </button>
        </div>
      </div>

      <div class="max-w-4xl mx-auto px-6 py-8 flex gap-8">
        <!-- Concept nav -->
        <nav class="w-52 shrink-0 hidden lg:block">
          <p class="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Concepts</p>
          <ul class="space-y-1">
            <li
              v-for="(c, idx) in path.concepts"
              :key="c.id"
            >
              <button
                class="w-full text-left px-3 py-2 rounded-lg text-xs transition-colors"
                :class="[
                  activeConcept === idx
                    ? 'bg-accent/10 text-accent font-medium'
                    : 'text-text-secondary hover:bg-surface-secondary',
                  c.status === 'pruned' ? 'line-through opacity-40' : '',
                ]"
                @click="activeConcept = idx"
              >
                <span class="mr-1.5 text-text-muted">{{ idx + 1 }}.</span>
                {{ c.title }}
                <svg v-if="c.locked" class="w-3 h-3 inline -mt-0.5 ml-1 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4m-2 0h12a2 2 0 012 2v6a2 2 0 01-2 2H6a2 2 0 01-2-2v-6a2 2 0 012-2z" />
                </svg>
                <span v-else-if="c.status === 'accepted'" class="ml-1 text-grounded">✓</span>
              </button>
            </li>
          </ul>
        </nav>

        <!-- Concept detail -->
        <main class="flex-1 min-w-0">
          <!-- Generating state -->
          <div v-if="path.status === 'generating'" class="flex flex-col items-center justify-center py-24 text-center">
            <div class="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mb-4" />
            <p class="text-sm font-medium text-text-primary">Generating learning path…</p>
            <p class="text-xs text-text-muted mt-1">The curriculum agent is reading the corpus. This takes a few minutes on CPU.</p>
          </div>

          <!-- Failed state -->
          <div v-else-if="path.status === 'failed'" class="flex flex-col items-center justify-center py-24 text-center">
            <svg class="w-8 h-8 text-warning mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
            <p class="text-sm font-medium text-text-primary">Generation failed</p>
            <p class="text-xs text-text-muted mt-1">The curriculum agent could not produce grounded concepts from this corpus. Try ingesting more sources.</p>
          </div>

          <!-- Owner analytics (KC-085) -->
          <div v-else-if="showAnalytics && isOwner">
            <div class="flex items-start justify-between gap-4 mb-6">
              <div>
                <p class="text-xs text-text-muted mb-1">Cohort analytics</p>
                <h2 class="text-xl font-semibold text-text-primary">Learners</h2>
              </div>
            </div>

            <p v-if="analyticsLoading" class="text-sm text-text-muted">Loading analytics…</p>
            <p v-else-if="analyticsError" class="text-sm text-warning">{{ analyticsError }}</p>

            <template v-else-if="analytics">
              <p v-if="analytics.learner_count === 0" class="text-sm text-text-muted">
                No learner activity yet. Progress and answer attempts appear here once someone works through the path.
              </p>

              <template v-else>
                <!-- Per-learner table -->
                <div class="rounded-xl border border-border overflow-hidden mb-6">
                  <table class="w-full text-xs">
                    <thead>
                      <tr class="border-b border-border bg-surface-secondary">
                        <th class="text-left px-3 py-2 text-text-muted font-medium">Learner</th>
                        <th class="text-right px-3 py-2 text-text-muted font-medium">Progress</th>
                        <th class="text-right px-3 py-2 text-text-muted font-medium">Attempts</th>
                        <th class="text-right px-3 py-2 text-text-muted font-medium">Correct</th>
                        <th class="text-right px-3 py-2 text-text-muted font-medium">Last activity</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="l in analytics.learners" :key="l.user.id" class="border-b border-border last:border-0">
                        <td class="px-3 py-2 text-text-primary">
                          @{{ l.user.handle }}
                          <span v-if="l.user.id === auth.user?.id" class="text-text-muted">(you)</span>
                        </td>
                        <td class="px-3 py-2 text-right text-text-primary">
                          {{ l.learned_count }}/{{ analytics.active_concept_count }}
                          <span class="text-text-muted">({{ Math.round(l.completion_pct * 100) }}%)</span>
                        </td>
                        <td class="px-3 py-2 text-right text-text-secondary">{{ l.attempt_count }}</td>
                        <td class="px-3 py-2 text-right">
                          <span v-if="l.attempt_count > 0" :class="l.correct_rate >= 0.8 ? 'text-grounded' : l.correct_rate >= 0.5 ? 'text-warning' : 'text-red-500'">
                            {{ Math.round(l.correct_rate * 100) }}%
                          </span>
                          <span v-else class="text-text-muted">—</span>
                        </td>
                        <td class="px-3 py-2 text-right text-text-muted">{{ fmtDateTime(l.last_activity) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- Per-concept table -->
                <h3 class="text-sm font-semibold text-text-primary mb-3">Concepts</h3>
                <div class="space-y-2">
                  <div v-for="c in analytics.concepts" :key="c.concept_id" class="rounded-xl border border-border p-4">
                    <div class="flex items-center justify-between gap-3">
                      <p class="text-sm text-text-primary font-medium">{{ c.position + 1 }}. {{ c.title }}</p>
                      <p class="text-xs text-text-muted shrink-0">
                        {{ c.learners_learned }} learned · {{ c.attempt_count }} attempt{{ c.attempt_count !== 1 ? 's' : '' }}
                        <template v-if="c.attempt_count > 0">
                          ·
                          <span :class="c.correct_rate >= 0.8 ? 'text-grounded' : c.correct_rate >= 0.5 ? 'text-warning' : 'text-red-500'">
                            {{ Math.round(c.correct_rate * 100) }}% correct
                          </span>
                        </template>
                      </p>
                    </div>
                    <div v-if="c.top_wrong_answers.length > 0" class="mt-2 space-y-1">
                      <p class="text-xs font-semibold text-text-muted uppercase tracking-wider">Common wrong answers</p>
                      <p v-for="w in c.top_wrong_answers" :key="w.answer_text" class="text-xs text-text-secondary">
                        “{{ w.answer_text }}” × {{ w.count }}
                        <span v-if="w.misconception_label" class="text-warning">— {{ w.misconception_label }}</span>
                      </p>
                    </div>
                  </div>
                </div>
              </template>
            </template>
          </div>

          <template v-else-if="path.concepts.length > 0">
            <div v-for="(concept, idx) in path.concepts" :key="concept.id" v-show="activeConcept === idx">
              <!-- Hard-locked concept — the server redacts its content (docs/14, OQ-48) -->
              <template v-if="isHardLocked(concept)">
                <div class="mb-6">
                  <p class="text-xs text-text-muted mb-1">Concept {{ idx + 1 }} of {{ path.concepts.length }}</p>
                  <h2 class="text-xl font-semibold text-text-primary">{{ concept.title }}</h2>
                </div>
                <div class="rounded-xl border border-border bg-surface-secondary p-10 text-center">
                  <svg class="w-8 h-8 mx-auto text-text-muted mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 11V7a4 4 0 00-8 0v4m-2 0h12a2 2 0 012 2v6a2 2 0 01-2 2H6a2 2 0 01-2-2v-6a2 2 0 012-2z" />
                  </svg>
                  <p class="text-sm font-medium text-text-primary mb-1">Locked by mastery gating</p>
                  <p class="text-xs text-text-muted">
                    {{ unlockHint(idx) ?? 'Master the previous concepts to unlock this one.' }}
                  </p>
                </div>
                <div class="flex justify-between mt-8 pt-6 border-t border-border">
                  <button
                    v-if="idx > 0"
                    class="text-sm text-text-secondary hover:text-accent flex items-center gap-1.5"
                    @click="activeConcept = idx - 1"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                    </svg>
                    Previous
                  </button>
                </div>
              </template>

              <template v-else>
              <!-- Concept header -->
              <div class="flex items-start justify-between gap-4 mb-6">
                <div>
                  <p class="text-xs text-text-muted mb-1">Concept {{ idx + 1 }} of {{ path.concepts.length }}</p>
                  <h2 class="text-xl font-semibold text-text-primary">{{ concept.title }}</h2>
                </div>
                <div class="flex gap-2 shrink-0">
                  <button
                    :disabled="learnedSaving[concept.id]"
                    class="text-xs px-3 py-1.5 rounded-full font-medium transition-colors disabled:opacity-50"
                    :class="learnedIds.has(concept.id)
                      ? 'bg-grounded text-white hover:bg-green-700'
                      : 'border border-border text-text-secondary hover:bg-surface-secondary'"
                    @click="toggleLearned(concept.id)"
                  >
                    {{ learnedIds.has(concept.id) ? '✓ Learned' : 'Mark learned' }}
                  </button>
                  <button
                    v-if="isOwner && concept.status !== 'accepted'"
                    class="text-xs px-3 py-1.5 rounded-lg border border-grounded text-grounded hover:bg-grounded/10 transition-colors"
                    @click="updateConceptStatus(concept, 'accepted')"
                  >
                    Accept
                  </button>
                  <button
                    v-if="isOwner && concept.status !== 'pruned'"
                    class="text-xs px-3 py-1.5 rounded-lg border border-border text-text-muted hover:bg-surface-secondary transition-colors"
                    @click="updateConceptStatus(concept, 'pruned')"
                  >
                    Prune
                  </button>
                </div>
              </div>

              <!-- Soft-gate warning (docs/14, OQ-48 — warns, never blocks) -->
              <div
                v-if="concept.locked && path.mastery_mode === 'soft'"
                class="rounded-xl border border-warning/40 bg-warning/5 p-4 mb-5"
              >
                <p class="text-xs text-warning font-medium mb-0.5">This concept is gated</p>
                <p class="text-xs text-text-secondary">
                  {{ unlockHint(idx) ?? 'Master the previous concepts first.' }}
                  You can keep going, but the path owner recommends mastering the previous concepts first.
                </p>
              </div>

              <!-- Explanation -->
              <div class="rounded-xl border border-border bg-surface-secondary p-5 mb-5">
                <p
                  v-if="concept.instructor_annotation"
                  class="font-prose text-text-primary text-sm leading-7"
                >
                  {{ concept.instructor_annotation }}
                </p>
                <p
                  v-else
                  class="font-prose text-text-primary text-sm leading-7"
                  v-html="highlightCitations(concept.explanation_text)"
                />
              </div>

              <!-- Private note (KC-047) -->
              <div class="rounded-xl border border-border bg-surface p-4 mb-5">
                <div class="flex items-center justify-between mb-2">
                  <p class="text-xs font-semibold text-text-secondary uppercase tracking-wider">My private note</p>
                  <span v-if="noteSaved[concept.id]" class="text-xs text-grounded">Saved</span>
                </div>
                <textarea
                  v-model="noteBodies[concept.id]"
                  rows="3"
                  placeholder="Only you can see this note."
                  class="w-full border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent resize-none"
                />
                <div class="flex justify-end mt-2">
                  <button
                    :disabled="noteSaving[concept.id]"
                    class="text-xs px-3 py-1.5 rounded-lg border border-border text-text-secondary hover:bg-surface-secondary disabled:opacity-50 transition-colors"
                    @click="saveNote(concept.id)"
                  >
                    {{ noteSaving[concept.id] ? 'Saving…' : 'Save note' }}
                  </button>
                </div>
              </div>

              <!-- Source passages toggle -->
              <button
                class="text-xs text-text-muted hover:text-accent flex items-center gap-1.5 mb-5"
                @click="showPassages[concept.id] = !showPassages[concept.id]"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="showPassages[concept.id] ? 'M19 9l-7 7-7-7' : 'M9 5l7 7-7 7'" />
                </svg>
                {{ concept.source_passages.length }} source passage{{ concept.source_passages.length !== 1 ? 's' : '' }}
              </button>

              <div v-if="showPassages[concept.id]" class="space-y-2 mb-5">
                <div
                  v-for="p in concept.source_passages"
                  :key="p.chunk_id"
                  class="rounded-lg border border-grounded/20 bg-grounded-light p-3"
                >
                  <a
                    v-if="passageDeepLink(p)"
                    :href="passageDeepLink(p)!"
                    target="_blank"
                    rel="noopener"
                    class="text-xs font-mono text-grounded mb-1 block underline decoration-dotted hover:text-accent"
                    title="Open the video at this timestamp"
                  >▶ {{ p.locator }}</a>
                  <p v-else class="text-xs font-mono text-grounded mb-1">{{ p.locator }}</p>
                  <p class="text-xs text-text-secondary leading-5">{{ p.excerpt }}</p>
                </div>
              </div>

              <!-- Assessment -->
              <div v-if="concept.assessment_items.length > 0" class="mt-6">
                <h3 class="text-sm font-semibold text-text-primary mb-4">Assessment</h3>
                <div
                  v-for="item in concept.assessment_items"
                  :key="item.id"
                  class="rounded-xl border border-border p-5 mb-4"
                >
                  <p class="text-sm text-text-primary font-medium mb-4">{{ item.question_text }}</p>

                  <!-- Multiple-choice buttons (when the item has distractor-backed choices) -->
                  <div v-if="item.choices.length > 0" class="space-y-2">
                    <button
                      v-for="choice in item.choices"
                      :key="choice.id"
                      :disabled="!!attemptResults[item.id] || submitting[item.id]"
                      class="w-full text-left px-3 py-2 rounded-lg border text-sm transition-colors disabled:cursor-default"
                      :class="attemptResults[item.id] && selectedAnswer[item.id] === choice.text
                        ? attemptResults[item.id].correct
                          ? 'border-grounded bg-grounded/5 text-grounded font-medium'
                          : 'border-warning bg-warning/5 text-warning font-medium'
                        : selectedAnswer[item.id] === choice.text
                          ? 'border-accent bg-accent/5 text-text-primary'
                          : 'border-border text-text-secondary hover:border-accent/40 hover:bg-surface-secondary'"
                      @click="selectedAnswer[item.id] = choice.text"
                    >
                      {{ choice.text }}
                    </button>
                  </div>

                  <!-- Free-text answer input (items without choices) -->
                  <input
                    v-else
                    v-model="selectedAnswer[item.id]"
                    type="text"
                    :disabled="!!attemptResults[item.id]"
                    placeholder="Type your answer…"
                    class="w-full px-3 py-2 rounded-lg border text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent transition-colors disabled:opacity-70"
                    :class="attemptResults[item.id]
                      ? attemptResults[item.id].correct
                        ? 'border-grounded bg-grounded/5'
                        : 'border-warning bg-warning/5'
                      : 'border-border focus:border-accent'"
                    @keyup.enter="submitAnswer(concept, item)"
                  />

                  <!-- Submit button -->
                  <div class="mt-4 flex items-center gap-4">
                    <button
                      v-if="!attemptResults[item.id]"
                      :disabled="!selectedAnswer[item.id] || submitting[item.id]"
                      class="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      @click="submitAnswer(concept, item)"
                    >
                      {{ submitting[item.id] ? 'Checking…' : 'Submit' }}
                    </button>

                    <!-- Result feedback -->
                    <div v-if="attemptResults[item.id]">
                      <p
                        class="text-sm font-medium"
                        :class="attemptResults[item.id].correct ? 'text-grounded' : 'text-warning'"
                      >
                        {{ attemptResults[item.id].correct ? '✓ Correct' : '✗ Incorrect' }}
                      </p>
                      <p v-if="!attemptResults[item.id].correct && attemptResults[item.id].correct_answer" class="text-xs text-text-muted mt-1">
                        Correct answer: <span class="text-text-primary">{{ attemptResults[item.id].correct_answer }}</span>
                      </p>
                      <p v-if="attemptResults[item.id].feedback" class="text-xs text-text-muted mt-1">
                        {{ attemptResults[item.id].feedback }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Discussion (KC-084) -->
              <div class="mt-6">
                <ConceptDiscussion
                  :path-id="pathId"
                  :concept-id="concept.id"
                  :source-passages="concept.source_passages"
                  :is-path-owner="isOwner"
                />
              </div>

              <!-- Navigation -->
              <div class="flex justify-between mt-8 pt-6 border-t border-border">
                <button
                  v-if="idx > 0"
                  class="text-sm text-text-secondary hover:text-accent flex items-center gap-1.5"
                  @click="activeConcept = idx - 1"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                  </svg>
                  Previous
                </button>
                <div v-else />
                <button
                  v-if="idx < path.concepts.length - 1"
                  class="text-sm text-accent hover:text-accent-hover flex items-center gap-1.5 ml-auto"
                  @click="activeConcept = idx + 1"
                >
                  Next
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
              </template>
            </div>
          </template>
          <p v-else class="text-text-muted text-sm">No concepts in this path.</p>
        </main>
      </div>
    </template>
  </div>
</template>
