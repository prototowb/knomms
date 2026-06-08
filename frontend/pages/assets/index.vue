<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

import { ref, computed, onMounted, watch } from 'vue'

const auth = useAuthStore()

interface AssetSummary {
  id: string
  title: string
  description: string
  asset_type: string
  visibility: string
  fork_count: number
  created_at: string
  owner: { id: string; handle: string; display_name: string } | null
  version_count: number
}

const assets = ref<AssetSummary[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

// Filters
const typeFilter = ref('')
const visibilityFilter = ref('')
const searchQuery = ref('')
const debouncedQ = ref('')

// Create form
const showCreate = ref(false)
const newTitle = ref('')
const newDesc = ref('')
const newType = ref('system_prompt')
const newVisibility = ref<'private' | 'team' | 'public'>('private')
const creating = ref(false)

const ASSET_TYPES = [
  { value: 'system_prompt', label: 'System Prompt' },
  { value: 'few_shot_set', label: 'Few-Shot Set' },
  { value: 'eval_suite', label: 'Eval Suite' },
  { value: 'chain_spec', label: 'Chain Spec' },
  { value: 'tool_spec', label: 'Tool Spec' },
]

let debounceTimer: ReturnType<typeof setTimeout> | null = null

watch(searchQuery, (v) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    debouncedQ.value = v.length >= 2 ? v : ''
  }, 300)
})

async function fetchAssets() {
  loading.value = true
  error.value = null
  try {
    const params: Record<string, string> = {}
    if (typeFilter.value) params.asset_type = typeFilter.value
    if (visibilityFilter.value) params.visibility = visibilityFilter.value
    if (debouncedQ.value) params.q = debouncedQ.value

    const qs = new URLSearchParams(params).toString()
    assets.value = await $fetch<AssetSummary[]>(`/api/assets${qs ? '?' + qs : ''}`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
  } catch {
    error.value = 'Failed to load assets'
  } finally {
    loading.value = false
  }
}

watch([typeFilter, visibilityFilter, debouncedQ], fetchAssets)

async function createAsset() {
  if (!newTitle.value.trim() || creating.value) return
  creating.value = true
  error.value = null
  try {
    const a = await $fetch<{ id: string }>('/api/assets', {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: {
        title: newTitle.value.trim(),
        description: newDesc.value.trim(),
        asset_type: newType.value,
        visibility: newVisibility.value,
      },
    })
    showCreate.value = false
    newTitle.value = ''
    newDesc.value = ''
    await navigateTo(`/assets/${a.id}`)
  } catch {
    error.value = 'Failed to create asset'
  } finally {
    creating.value = false
  }
}

const typeLabel: Record<string, string> = {
  system_prompt: 'System Prompt',
  few_shot_set: 'Few-Shot Set',
  eval_suite: 'Eval Suite',
  chain_spec: 'Chain Spec',
  tool_spec: 'Tool Spec',
}

const typeColor: Record<string, string> = {
  system_prompt: 'text-accent bg-accent/10',
  few_shot_set: 'text-grounded bg-grounded/10',
  eval_suite: 'text-warning bg-warning/10',
  chain_spec: 'text-text-secondary bg-border',
  tool_spec: 'text-text-secondary bg-border',
}

const visibilityColor: Record<string, string> = {
  private: 'text-text-muted bg-border',
  team: 'text-accent bg-accent/10',
  public: 'text-grounded bg-grounded/10',
}

onMounted(fetchAssets)
</script>

<template>
  <div class="max-w-3xl mx-auto py-10 px-6">
    <header class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-text-primary">AI Assets</h1>
        <p class="text-sm text-text-muted mt-0.5">Versioned prompts, eval suites, and harness components</p>
      </div>
      <button
        class="px-3 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover transition-colors"
        @click="showCreate = !showCreate"
      >
        + New asset
      </button>
    </header>

    <!-- Create form -->
    <div v-if="showCreate" class="mb-6 rounded-xl border border-accent/30 bg-accent/5 p-5 space-y-3">
      <h2 class="text-sm font-semibold text-text-primary">New asset</h2>
      <input
        v-model="newTitle"
        type="text"
        placeholder="Asset title"
        class="w-full border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
        @keydown.enter="createAsset"
      />
      <textarea
        v-model="newDesc"
        placeholder="Description (optional)"
        rows="2"
        class="w-full border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent resize-none"
      />
      <div class="flex items-center gap-3 flex-wrap">
        <select
          v-model="newType"
          class="border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface focus:outline-none focus:border-accent"
        >
          <option v-for="t in ASSET_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
        </select>
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
          @click="createAsset"
        >
          {{ creating ? 'Creating…' : 'Create' }}
        </button>
      </div>
    </div>

    <!-- Filters + search -->
    <div class="flex items-center gap-3 mb-5 flex-wrap">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search title, description, rationale…"
        class="flex-1 min-w-48 border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
      />
      <select
        v-model="typeFilter"
        class="border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface focus:outline-none focus:border-accent"
      >
        <option value="">All types</option>
        <option v-for="t in ASSET_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
      </select>
      <select
        v-model="visibilityFilter"
        class="border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface focus:outline-none focus:border-accent"
      >
        <option value="">All visibility</option>
        <option value="private">Private</option>
        <option value="team">Team</option>
        <option value="public">Public</option>
      </select>
    </div>

    <p v-if="error" class="text-sm text-warning mb-4">{{ error }}</p>

    <div v-if="loading" class="space-y-3">
      <div v-for="n in 4" :key="n" class="h-16 rounded-xl bg-border/40 animate-pulse" />
    </div>

    <div v-else-if="assets.length === 0" class="text-center py-16 text-text-muted">
      <p class="text-sm">{{ searchQuery || typeFilter || visibilityFilter ? 'No assets match the current filters.' : 'No assets yet.' }}</p>
      <button v-if="!searchQuery && !typeFilter && !visibilityFilter" class="mt-2 text-sm text-accent hover:underline" @click="showCreate = true">
        Create your first asset
      </button>
    </div>

    <ul v-else class="space-y-3">
      <li v-for="a in assets" :key="a.id">
        <NuxtLink
          :to="`/assets/${a.id}`"
          class="group flex items-start gap-4 rounded-xl border border-border bg-surface p-4 hover:border-accent/40 hover:shadow-sm transition-all"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-text-primary group-hover:text-accent transition-colors truncate">
              {{ a.title }}
            </p>
            <p v-if="a.description" class="text-xs text-text-muted mt-0.5 truncate">{{ a.description }}</p>
            <div class="flex items-center gap-2 mt-1.5">
              <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="typeColor[a.asset_type] ?? 'text-text-muted bg-border'">
                {{ typeLabel[a.asset_type] ?? a.asset_type }}
              </span>
              <span class="text-xs text-text-muted">
                {{ a.version_count }} version{{ a.version_count !== 1 ? 's' : '' }}
              </span>
              <span v-if="a.fork_count > 0" class="text-xs text-text-muted">
                · {{ a.fork_count }} fork{{ a.fork_count !== 1 ? 's' : '' }}
              </span>
            </div>
          </div>
          <span class="shrink-0 text-xs px-2 py-0.5 rounded-full font-medium" :class="visibilityColor[a.visibility] ?? ''">
            {{ a.visibility }}
          </span>
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
