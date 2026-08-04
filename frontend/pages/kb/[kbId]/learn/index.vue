<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

import { ref, onMounted } from 'vue'
import { useAuthStore } from '~/stores/auth'

const route = useRoute()
const kbId = route.params.kbId as string
const auth = useAuthStore()

interface LearningPathSummary {
  id: string
  kb_id: string
  learning_goal: string
  status: string
  version: number
  concept_count: number
  created_at: string
}

const paths = ref<LearningPathSummary[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const generating = ref(false)
const learningGoal = ref('')
const showNewForm = ref(false)

async function fetchPaths() {
  loading.value = true
  error.value = null
  try {
    const data = await $fetch<LearningPathSummary[]>(`/api/kb/${kbId}/learning-paths`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    paths.value = data
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to load learning paths'
  } finally {
    loading.value = false
  }
}

async function generatePath() {
  if (!learningGoal.value.trim() || generating.value) return
  generating.value = true
  error.value = null
  try {
    const data = await $fetch<{ id: string }>(`/api/kb/${kbId}/learning-paths`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { learning_goal: learningGoal.value.trim() },
    })
    learningGoal.value = ''
    showNewForm.value = false
    await navigateTo(`/learn/${data.id}`)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to generate learning path'
  } finally {
    generating.value = false
  }
}

const statusColor: Record<string, string> = {
  generating: 'text-text-muted bg-border',
  draft: 'text-warning bg-warning/10',
  published: 'text-grounded bg-grounded/10',
  failed: 'text-warning bg-warning/10',
}

onMounted(fetchPaths)
</script>

<template>
  <div class="max-w-2xl mx-auto py-10 px-6">
    <header class="flex items-start justify-between mb-8">
      <div>
        <NuxtLink :to="`/kb/${kbId}`" class="text-xs text-text-muted hover:text-accent mb-2 flex items-center gap-1">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
          Back to KB
        </NuxtLink>
        <h1 class="text-2xl font-semibold text-text-primary">Learning Paths</h1>
        <p class="text-sm text-text-muted mt-1">AI-generated from this knowledge base</p>
      </div>
      <button
        class="px-3 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover transition-colors"
        @click="showNewForm = !showNewForm"
      >
        + New path
      </button>
    </header>

    <!-- Generate new path form -->
    <div
      v-if="showNewForm"
      class="mb-6 rounded-xl border border-accent/30 bg-accent/5 p-5"
    >
      <h2 class="text-sm font-semibold text-text-primary mb-3">Generate a learning path</h2>
      <p class="text-xs text-text-muted mb-4">
        The curriculum agent will read this KB's corpus and propose a grounded sequence of concepts with assessments.
      </p>
      <div class="flex gap-3">
        <input
          v-model="learningGoal"
          type="text"
          placeholder="Learning goal, e.g. &#x27;Understand the end-to-end ingestion pipeline&#x27;"
          :disabled="generating"
          class="flex-1 border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50"
          @keydown.enter="generatePath"
        />
        <button
          :disabled="generating || !learningGoal.trim()"
          class="px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          @click="generatePath"
        >
          {{ generating ? 'Generating…' : 'Generate' }}
        </button>
      </div>
      <p v-if="generating" class="text-xs text-text-muted mt-3">
        This may take a minute — the agent is reading the corpus and building concept proposals.
      </p>
    </div>

    <p v-if="error" class="text-sm text-warning mb-4">{{ error }}</p>

    <div v-if="loading" class="space-y-3">
      <div v-for="n in 3" :key="n" class="h-20 rounded-xl bg-border/40 animate-pulse" />
    </div>

    <div v-else-if="paths.length === 0" class="text-center py-16 text-text-muted">
      <svg class="w-10 h-10 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
      <p class="text-sm">No learning paths yet.</p>
      <button
        class="mt-3 text-sm text-accent hover:underline"
        @click="showNewForm = true"
      >
        Generate your first path
      </button>
    </div>

    <ul v-else class="space-y-3">
      <li
        v-for="p in paths"
        :key="p.id"
      >
        <NuxtLink
          :to="`/learn/${p.id}`"
          class="block rounded-xl border border-border bg-surface p-5 hover:border-accent/40 hover:shadow-sm transition-all"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <p class="font-medium text-text-primary text-sm truncate">{{ p.learning_goal }}</p>
              <p class="text-xs text-text-muted mt-1">
                {{ p.concept_count }} concept{{ p.concept_count !== 1 ? 's' : '' }} · v{{ p.version }}
              </p>
            </div>
            <span
              class="shrink-0 text-xs px-2 py-0.5 rounded-full font-medium"
              :class="statusColor[p.status] ?? 'text-text-muted bg-border'"
            >
              {{ p.status }}
            </span>
          </div>
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
