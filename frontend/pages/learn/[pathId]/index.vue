<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '~/stores/auth'

const route = useRoute()
const pathId = route.params.pathId as string
const auth = useAuthStore()

interface Distractor {
  id: string
  text: string
  why_wrong_passage_id: string
  misconception_label: string | null
}

interface AssessmentItem {
  id: string
  question_text: string
  correct_answer: string
  grounding_passage_id: string
  distractors: Distractor[]
}

interface SourcePassage {
  chunk_id: string
  locator: string
  source_id: string
  excerpt: string
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
}

interface LearningPath {
  id: string
  kb_id: string
  learning_goal: string
  status: string
  version: number
  concepts: PathConcept[]
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

async function fetchPath() {
  loading.value = true
  try {
    const data = await $fetch<LearningPath>(`/api/learning-paths/${pathId}`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    path.value = data
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to load learning path'
  } finally {
    loading.value = false
  }
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
  } catch {
    // keep selected, let user retry
  } finally {
    submitting.value[item.id] = false
  }
}

async function publishPath() {
  if (!path.value) return
  await $fetch(`/api/learning-paths/${pathId}/publish`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${auth.token}` },
  })
  if (path.value) path.value.status = 'published'
}

const acceptedCount = computed(() =>
  path.value?.concepts.filter(c => c.status === 'accepted').length ?? 0
)
const conceptCount = computed(() => path.value?.concepts.length ?? 0)

function highlightCitations(text: string): string {
  return text.replace(
    /\[SOURCE:([a-f0-9-]{36})\]/g,
    '<sup class="text-grounded font-mono text-xs">[src]</sup>'
  )
}

onMounted(fetchPath)
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
            v-if="path.status === 'draft'"
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
          <button
            v-if="path.status === 'draft'"
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
                <span v-if="c.status === 'accepted'" class="ml-1 text-grounded">✓</span>
              </button>
            </li>
          </ul>
        </nav>

        <!-- Concept detail -->
        <main class="flex-1 min-w-0">
          <template v-if="path.concepts.length > 0">
            <div v-for="(concept, idx) in path.concepts" :key="concept.id" v-show="activeConcept === idx">
              <!-- Concept header -->
              <div class="flex items-start justify-between gap-4 mb-6">
                <div>
                  <p class="text-xs text-text-muted mb-1">Concept {{ idx + 1 }} of {{ path.concepts.length }}</p>
                  <h2 class="text-xl font-semibold text-text-primary">{{ concept.title }}</h2>
                </div>
                <div class="flex gap-2 shrink-0">
                  <button
                    v-if="concept.status !== 'accepted'"
                    class="text-xs px-3 py-1.5 rounded-lg border border-grounded text-grounded hover:bg-grounded/10 transition-colors"
                    @click="$fetch(`/api/learning-paths/${pathId}/concepts/${concept.id}`, { method: 'PATCH', headers: { Authorization: `Bearer ${auth.token}` }, body: { status: 'accepted' } }).then(() => concept.status = 'accepted')"
                  >
                    Accept
                  </button>
                  <button
                    v-if="concept.status !== 'pruned'"
                    class="text-xs px-3 py-1.5 rounded-lg border border-border text-text-muted hover:bg-surface-secondary transition-colors"
                    @click="$fetch(`/api/learning-paths/${pathId}/concepts/${concept.id}`, { method: 'PATCH', headers: { Authorization: `Bearer ${auth.token}` }, body: { status: 'pruned' } }).then(() => concept.status = 'pruned')"
                  >
                    Prune
                  </button>
                </div>
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
                  <p class="text-xs font-mono text-grounded mb-1">{{ p.locator }}</p>
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

                  <!-- Answer choices -->
                  <div class="space-y-2">
                    <label
                      v-for="choice in [item.correct_answer, ...item.distractors.map(d => d.text)]"
                      :key="choice"
                      class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
                      :class="[
                        selectedAnswer[item.id] === choice
                          ? 'border-accent bg-accent/5'
                          : 'border-border hover:border-border-strong',
                        attemptResults[item.id] ? 'cursor-default pointer-events-none' : '',
                        attemptResults[item.id] && choice === item.correct_answer ? 'border-grounded bg-grounded/5' : '',
                        attemptResults[item.id] && selectedAnswer[item.id] === choice && !attemptResults[item.id].correct ? 'border-warning bg-warning/5' : '',
                      ]"
                    >
                      <input
                        v-model="selectedAnswer[item.id]"
                        type="radio"
                        :name="`item-${item.id}`"
                        :value="choice"
                        :disabled="!!attemptResults[item.id]"
                        class="mt-0.5 accent-accent"
                      />
                      <span class="text-sm text-text-primary">{{ choice }}</span>
                    </label>
                  </div>

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
            </div>
          </template>
          <p v-else class="text-text-muted text-sm">No concepts in this path.</p>
        </main>
      </div>
    </template>
  </div>
</template>
