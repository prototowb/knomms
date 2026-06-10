<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

import { ref, onMounted } from 'vue'

const auth = useAuthStore()

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

const harnesses = ref<HarnessSummary[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const showCreate = ref(false)
const newTitle = ref('')
const newDesc = ref('')
const newVisibility = ref<'private' | 'team' | 'public'>('private')
const creating = ref(false)

const visibilityColor: Record<string, string> = {
  private: 'text-text-muted bg-border',
  team: 'text-accent bg-accent/10',
  public: 'text-grounded bg-grounded/10',
}

async function fetchHarnesses() {
  loading.value = true
  error.value = null
  try {
    harnesses.value = await $fetch<HarnessSummary[]>('/api/harnesses', {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
  } catch {
    error.value = 'Failed to load harnesses'
  } finally {
    loading.value = false
  }
}

async function createHarness() {
  if (!newTitle.value.trim() || creating.value) return
  creating.value = true
  error.value = null
  try {
    const h = await $fetch<{ id: string }>('/api/harnesses', {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: {
        title: newTitle.value.trim(),
        description: newDesc.value.trim(),
        visibility: newVisibility.value,
      },
    })
    await navigateTo(`/harnesses/${h.id}/compose`)
  } catch {
    error.value = 'Failed to create harness'
  } finally {
    creating.value = false
  }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

onMounted(fetchHarnesses)
</script>

<template>
  <div class="max-w-3xl mx-auto py-10 px-6">
    <header class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-text-primary">Harnesses</h1>
        <p class="text-sm text-text-muted mt-0.5">Composed prompt assemblies with eval suites for local testing</p>
      </div>
      <button
        class="px-3 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover transition-colors"
        @click="showCreate = !showCreate"
      >
        + New harness
      </button>
    </header>

    <!-- Create form -->
    <div v-if="showCreate" class="mb-6 rounded-xl border border-accent/30 bg-accent/5 p-5 space-y-3">
      <h2 class="text-sm font-semibold text-text-primary">New harness</h2>
      <input
        v-model="newTitle"
        type="text"
        placeholder="Harness title"
        class="w-full border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
        @keydown.enter="createHarness"
      />
      <textarea
        v-model="newDesc"
        placeholder="Description (optional)"
        rows="2"
        class="w-full border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent resize-none"
      />
      <div class="flex items-center gap-3">
        <select
          v-model="newVisibility"
          class="border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface focus:outline-none focus:border-accent"
        >
          <option value="private">Private</option>
          <option value="team">Team</option>
          <option value="public">Public</option>
        </select>
        <button
          :disabled="creating || !newTitle.trim()"
          class="ml-auto px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
          @click="createHarness"
        >
          {{ creating ? 'Creating…' : 'Create' }}
        </button>
      </div>
    </div>

    <p v-if="error" class="text-sm text-warning mb-4">{{ error }}</p>

    <div v-if="loading" class="space-y-3">
      <div v-for="n in 3" :key="n" class="h-16 rounded-xl bg-border/40 animate-pulse" />
    </div>

    <div v-else-if="harnesses.length === 0" class="text-center py-16 text-text-muted">
      <p class="text-sm">No harnesses yet.</p>
      <button class="mt-2 text-sm text-accent hover:underline" @click="showCreate = true">
        Create your first harness
      </button>
    </div>

    <ul v-else class="space-y-3">
      <li v-for="h in harnesses" :key="h.id">
        <NuxtLink
          :to="`/harnesses/${h.id}/compose`"
          class="group flex items-start gap-4 rounded-xl border border-border bg-surface p-4 hover:border-accent/40 hover:shadow-sm transition-all"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-text-primary group-hover:text-accent transition-colors truncate">
              {{ h.title }}
            </p>
            <p v-if="h.description" class="text-xs text-text-muted mt-0.5 truncate">{{ h.description }}</p>
            <div class="flex items-center gap-2 mt-1.5 text-xs text-text-muted">
              <span>{{ h.asset_count }} slot{{ h.asset_count !== 1 ? 's' : '' }}</span>
              <span v-if="h.fork_count > 0">· {{ h.fork_count }} fork{{ h.fork_count !== 1 ? 's' : '' }}</span>
              <span>· {{ formatDate(h.created_at) }}</span>
            </div>
          </div>
          <span class="shrink-0 text-xs px-2 py-0.5 rounded-full font-medium" :class="visibilityColor[h.visibility] ?? ''">
            {{ h.visibility }}
          </span>
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
