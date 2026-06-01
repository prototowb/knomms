<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const auth = useAuthStore()

interface KBOut {
  id: string
  title: string
  index_status: string
  created_at: string
}

const kbs = ref<KBOut[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const showCreateForm = ref(false)
const newKBTitle = ref('')
const creating = ref(false)

async function fetchKBs() {
  loading.value = true
  try {
    kbs.value = await $fetch<KBOut[]>('/api/kbs', {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
  } catch {
    error.value = 'Failed to load knowledge bases'
  } finally {
    loading.value = false
  }
}

async function createKB() {
  if (!newKBTitle.value.trim() || creating.value) return
  creating.value = true
  try {
    const kb = await $fetch<KBOut>('/api/kbs', {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { title: newKBTitle.value.trim() },
    })
    kbs.value.unshift(kb)
    newKBTitle.value = ''
    showCreateForm.value = false
  } catch {
    error.value = 'Failed to create knowledge base'
  } finally {
    creating.value = false
  }
}

const statusLabel: Record<string, { text: string; cls: string }> = {
  building: { text: 'Building', cls: 'text-warning bg-warning/10' },
  ready: { text: 'Ready', cls: 'text-grounded bg-grounded/10' },
  stale: { text: 'Stale', cls: 'text-text-muted bg-border' },
  rebuilding: { text: 'Rebuilding', cls: 'text-warning bg-warning/10' },
}

onMounted(fetchKBs)
</script>

<template>
  <div class="max-w-3xl mx-auto py-10 px-6">
    <header class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-2xl font-semibold text-text-primary">
          Hello, {{ auth.user?.display_name || auth.user?.handle }}
        </h1>
        <p class="text-sm text-text-muted mt-0.5">Your knowledge bases</p>
      </div>
      <button
        class="px-3 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover transition-colors"
        @click="showCreateForm = !showCreateForm"
      >
        + New KB
      </button>
    </header>

    <!-- Create KB form -->
    <div v-if="showCreateForm" class="mb-6 rounded-xl border border-accent/30 bg-accent/5 p-5">
      <h2 class="text-sm font-semibold text-text-primary mb-3">New knowledge base</h2>
      <div class="flex gap-3">
        <input
          v-model="newKBTitle"
          type="text"
          placeholder="e.g. Urban Climate Resilience"
          :disabled="creating"
          class="flex-1 border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50"
          @keydown.enter="createKB"
        />
        <button
          :disabled="creating || !newKBTitle.trim()"
          class="px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
          @click="createKB"
        >
          {{ creating ? 'Creating…' : 'Create' }}
        </button>
      </div>
    </div>

    <p v-if="error" class="text-sm text-warning mb-4">{{ error }}</p>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-3">
      <div v-for="n in 3" :key="n" class="h-16 rounded-xl bg-border/40 animate-pulse" />
    </div>

    <!-- Empty state -->
    <div v-else-if="kbs.length === 0" class="text-center py-16 text-text-muted">
      <svg class="w-10 h-10 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
      <p class="text-sm">No knowledge bases yet.</p>
      <p class="text-xs mt-1">
        Create one above, or
        <NuxtLink to="/explore" class="text-accent hover:underline">fork a public board</NuxtLink>
        from the Explore page.
      </p>
    </div>

    <!-- KB list -->
    <ul v-else class="space-y-3">
      <li v-for="kb in kbs" :key="kb.id">
        <NuxtLink
          :to="`/kb/${kb.id}`"
          class="group flex items-center gap-4 rounded-xl border border-border bg-surface p-4 hover:border-accent/40 hover:shadow-sm transition-all"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-text-primary group-hover:text-accent transition-colors truncate">
              {{ kb.title }}
            </p>
            <p class="text-xs text-text-muted mt-0.5">
              Created {{ new Date(kb.created_at).toLocaleDateString() }}
            </p>
          </div>
          <span
            class="shrink-0 text-xs px-2 py-0.5 rounded-full font-medium"
            :class="statusLabel[kb.index_status]?.cls ?? 'text-text-muted bg-border'"
          >
            {{ statusLabel[kb.index_status]?.text ?? kb.index_status }}
          </span>
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
