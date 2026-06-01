<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

import { ref, onMounted } from 'vue'

const auth = useAuthStore()

interface BoardSummary {
  id: string
  title: string
  description: string
  visibility: string
  fork_count: number
  item_count: number
  ai_summary: string | null
  created_at: string
}

const boards = ref<BoardSummary[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const showCreateForm = ref(false)
const newTitle = ref('')
const newDesc = ref('')
const newVisibility = ref<'private' | 'public'>('private')
const creating = ref(false)

async function fetchBoards() {
  loading.value = true
  try {
    boards.value = await $fetch<BoardSummary[]>('/api/my/boards', {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
  } catch {
    error.value = 'Failed to load boards'
  } finally {
    loading.value = false
  }
}

async function createBoard() {
  if (!newTitle.value.trim() || creating.value) return
  creating.value = true
  try {
    const b = await $fetch<BoardSummary>('/api/boards', {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { title: newTitle.value.trim(), description: newDesc.value.trim(), visibility: newVisibility.value },
    })
    boards.value.unshift(b)
    newTitle.value = ''
    newDesc.value = ''
    showCreateForm.value = false
    await navigateTo(`/boards/${b.id}`)
  } catch {
    error.value = 'Failed to create board'
  } finally {
    creating.value = false
  }
}

const visibilityBadge: Record<string, string> = {
  private: 'text-text-muted bg-border',
  public: 'text-grounded bg-grounded/10',
  team: 'text-accent bg-accent/10',
}

onMounted(fetchBoards)
</script>

<template>
  <div class="max-w-3xl mx-auto py-10 px-6">
    <header class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-2xl font-semibold text-text-primary">My Boards</h1>
        <p class="text-sm text-text-muted mt-0.5">Curated knowledge collections</p>
      </div>
      <button
        class="px-3 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover transition-colors"
        @click="showCreateForm = !showCreateForm"
      >
        + New board
      </button>
    </header>

    <!-- Create form -->
    <div v-if="showCreateForm" class="mb-6 rounded-xl border border-accent/30 bg-accent/5 p-5 space-y-3">
      <h2 class="text-sm font-semibold text-text-primary">New board</h2>
      <input
        v-model="newTitle"
        type="text"
        placeholder="Board title"
        class="w-full border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
        @keydown.enter="createBoard"
      />
      <textarea
        v-model="newDesc"
        placeholder="Description (optional)"
        rows="2"
        class="w-full border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent resize-none"
      />
      <div class="flex items-center gap-4">
        <label class="flex items-center gap-2 cursor-pointer">
          <input v-model="newVisibility" type="radio" value="private" class="accent-accent" />
          <span class="text-sm text-text-secondary">Private</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input v-model="newVisibility" type="radio" value="public" class="accent-accent" />
          <span class="text-sm text-text-secondary">Public</span>
        </label>
        <button
          :disabled="creating || !newTitle.trim()"
          class="ml-auto px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
          @click="createBoard"
        >
          {{ creating ? 'Creating…' : 'Create' }}
        </button>
      </div>
    </div>

    <p v-if="error" class="text-sm text-warning mb-4">{{ error }}</p>

    <div v-if="loading" class="space-y-3">
      <div v-for="n in 3" :key="n" class="h-16 rounded-xl bg-border/40 animate-pulse" />
    </div>

    <div v-else-if="boards.length === 0" class="text-center py-16 text-text-muted">
      <p class="text-sm">No boards yet.</p>
      <button class="mt-2 text-sm text-accent hover:underline" @click="showCreateForm = true">
        Create your first board
      </button>
    </div>

    <ul v-else class="space-y-3">
      <li v-for="b in boards" :key="b.id">
        <NuxtLink
          :to="`/boards/${b.id}`"
          class="group flex items-center gap-4 rounded-xl border border-border bg-surface p-4 hover:border-accent/40 hover:shadow-sm transition-all"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-text-primary group-hover:text-accent transition-colors truncate">
              {{ b.title }}
            </p>
            <p class="text-xs text-text-muted mt-0.5">
              {{ b.item_count }} source{{ b.item_count !== 1 ? 's' : '' }}
              · {{ b.fork_count }} fork{{ b.fork_count !== 1 ? 's' : '' }}
            </p>
          </div>
          <span class="shrink-0 text-xs px-2 py-0.5 rounded-full font-medium" :class="visibilityBadge[b.visibility] ?? ''">
            {{ b.visibility }}
          </span>
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
