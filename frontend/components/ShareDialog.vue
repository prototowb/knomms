<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const props = defineProps<{
  // BFF path segment — matches the backend grants nesting
  resourceType: 'kbs' | 'assets' | 'harnesses'
  resourceId: string
  resourceTitle: string
}>()

const emit = defineEmits<{ (e: 'close'): void }>()

interface GrantOut {
  id: string
  principal_type: 'user' | 'team'
  principal_id: string
  principal_label: string
  permission: 'viewer' | 'editor'
  created_at: string
}

interface TeamSummary {
  id: string
  name: string
  member_count: number
  is_member: boolean
  can_manage: boolean
  created_at: string
}

const auth = useAuthStore()

const grants = ref<GrantOut[]>([])
const teams = ref<TeamSummary[]>([])
const loading = ref(true)
const busy = ref(false)
const error = ref<string | null>(null)

const principalType = ref<'user' | 'team'>('user')
const handle = ref('')
const teamId = ref('')
const permission = ref<'viewer' | 'editor'>('viewer')

const base = computed(() => `/api/${props.resourceType}/${props.resourceId}/grants`)
const authHeaders = computed(() => ({ Authorization: `Bearer ${auth.token}` }))

const canSubmit = computed(() =>
  principalType.value === 'user' ? handle.value.trim().length > 0 : teamId.value.length > 0
)

async function load() {
  loading.value = true
  try {
    const [grantList, teamList] = await Promise.all([
      $fetch<GrantOut[]>(base.value, { headers: authHeaders.value }).catch(() => []),
      // Teams exist only for org members; org-less owners just share to users
      auth.user?.org_id
        ? $fetch<TeamSummary[]>('/api/orgs/teams', { headers: authHeaders.value }).catch(() => [])
        : Promise.resolve([]),
    ])
    grants.value = grantList
    teams.value = teamList
  } finally {
    loading.value = false
  }
}

async function upsert(principal: string, type: 'user' | 'team', perm: 'viewer' | 'editor') {
  if (busy.value) return
  busy.value = true
  error.value = null
  try {
    await $fetch(base.value, {
      method: 'POST',
      headers: authHeaders.value,
      body: { principal_type: type, principal, permission: perm },
    })
    handle.value = ''
    teamId.value = ''
    await load()
  } catch (e: unknown) {
    const code = (e as { statusCode?: number }).statusCode
    error.value =
      code === 404
        ? type === 'user' ? 'No user with that handle' : 'Team not found'
        : code === 409
          ? 'The owner does not need a grant'
          : 'Failed to share'
  } finally {
    busy.value = false
  }
}

function addGrant() {
  if (!canSubmit.value) return
  const principal = principalType.value === 'user' ? handle.value.trim() : teamId.value
  upsert(principal, principalType.value, permission.value)
}

function changePermission(g: GrantOut, perm: 'viewer' | 'editor') {
  // POST upserts — re-sharing the same principal updates the permission
  const principal = g.principal_type === 'user' ? g.principal_label : g.principal_id
  upsert(principal, g.principal_type, perm)
}

async function revoke(g: GrantOut) {
  if (busy.value) return
  busy.value = true
  error.value = null
  try {
    await $fetch(`${base.value}/${g.id}`, { method: 'DELETE', headers: authHeaders.value })
    await load()
  } catch {
    error.value = 'Failed to revoke'
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
    @click.self="emit('close')"
  >
    <div class="bg-surface rounded-2xl shadow-xl p-6 w-full max-w-md">
      <div class="flex items-start justify-between gap-3 mb-1">
        <h2 class="text-base font-semibold text-text-primary">Share</h2>
        <button class="text-text-muted hover:text-text-primary" aria-label="Close" @click="emit('close')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <p class="text-xs text-text-muted mb-4 truncate">{{ resourceTitle }}</p>

      <p v-if="error" class="mb-3 px-3 py-2 rounded-lg text-xs bg-red-50 text-red-700 border border-red-200">
        {{ error }}
      </p>

      <!-- Add grant -->
      <form class="flex flex-col gap-2 mb-5" @submit.prevent="addGrant">
        <div class="flex gap-2">
          <select
            v-model="principalType"
            class="px-2 py-2 rounded-lg border border-border bg-surface-secondary text-sm text-text-primary focus:outline-none focus:border-accent"
          >
            <option value="user">User</option>
            <option v-if="teams.length > 0" value="team">Team</option>
          </select>
          <input
            v-if="principalType === 'user'"
            v-model="handle"
            type="text"
            placeholder="Exact handle, e.g. ada"
            class="flex-1 min-w-0 px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent"
          >
          <select
            v-else
            v-model="teamId"
            class="flex-1 min-w-0 px-2 py-2 rounded-lg border border-border bg-surface-secondary text-sm text-text-primary focus:outline-none focus:border-accent"
          >
            <option value="" disabled>Pick a team…</option>
            <option v-for="t in teams" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <select
            v-model="permission"
            class="px-2 py-2 rounded-lg border border-border bg-surface-secondary text-sm text-text-primary focus:outline-none focus:border-accent"
          >
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
          </select>
        </div>
        <button
          type="submit"
          :disabled="!canSubmit || busy"
          class="px-3 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover transition-colors disabled:opacity-50"
        >
          Share
        </button>
        <p class="text-[11px] leading-4 text-text-muted">
          Viewers can read and query. Editors can also add sources, commit versions, or run evals —
          depending on what this is. Only you can change visibility or sharing.
        </p>
      </form>

      <!-- Existing grants -->
      <h3 class="text-xs font-semibold text-text-primary mb-2">Shared with</h3>
      <p v-if="loading" class="text-xs text-text-muted">Loading…</p>
      <p v-else-if="grants.length === 0" class="text-xs text-text-muted">Nobody yet — grants are private, targeted shares.</p>
      <ul v-else class="divide-y divide-border max-h-56 overflow-y-auto">
        <li v-for="g in grants" :key="g.id" class="flex items-center gap-2 py-2">
          <span
            class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium uppercase tracking-wide"
            :class="g.principal_type === 'team' ? 'bg-accent/10 text-accent' : 'bg-border text-text-secondary'"
          >
            {{ g.principal_type }}
          </span>
          <span class="flex-1 min-w-0 text-sm text-text-primary truncate">
            {{ g.principal_type === 'user' ? '@' + g.principal_label : g.principal_label }}
          </span>
          <select
            :value="g.permission"
            :disabled="busy"
            class="px-1.5 py-1 rounded border border-border bg-surface-secondary text-xs text-text-primary focus:outline-none"
            @change="changePermission(g, ($event.target as HTMLSelectElement).value as 'viewer' | 'editor')"
          >
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
          </select>
          <button
            :disabled="busy"
            class="text-xs text-text-muted hover:text-red-600 transition-colors disabled:opacity-50"
            @click="revoke(g)"
          >
            Revoke
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>
