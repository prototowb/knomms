<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

import { ref, computed, onMounted } from 'vue'

const auth = useAuthStore()

interface OrgMember {
  id: string
  handle: string
  display_name: string
  org_role: 'admin' | 'member'
}

interface Org {
  id: string
  name: string
  created_at: string
  members: OrgMember[]
  invite_code: string | null
}

const org = ref<Org | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const busy = ref(false)

const newName = ref('')
const joinCode = ref('')
const copied = ref(false)

const isAdmin = computed(() => auth.user?.org_role === 'admin')
const isSelf = (m: OrgMember) => m.id === auth.user?.id

async function fetchOrg() {
  loading.value = true
  error.value = null
  try {
    org.value = await $fetch<Org>('/api/orgs/me', {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
  } catch (e: unknown) {
    // 404 = org-less, the create/join surface — anything else is a real error
    if ((e as { statusCode?: number }).statusCode !== 404) {
      error.value = 'Failed to load organisation'
    }
    org.value = null
  } finally {
    loading.value = false
  }
}

async function refresh() {
  // Membership changes also change auth.user.org_id/org_role
  await Promise.all([fetchOrg(), auth.fetchMe()])
}

async function createOrg() {
  if (!newName.value.trim() || busy.value) return
  busy.value = true
  error.value = null
  try {
    await $fetch('/api/orgs', {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { name: newName.value.trim() },
    })
    newName.value = ''
    await refresh()
  } catch {
    error.value = 'Failed to create organisation'
  } finally {
    busy.value = false
  }
}

async function joinOrg() {
  if (!joinCode.value.trim() || busy.value) return
  busy.value = true
  error.value = null
  try {
    await $fetch('/api/orgs/join', {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { invite_code: joinCode.value.trim() },
    })
    joinCode.value = ''
    await refresh()
  } catch (e: unknown) {
    error.value = (e as { statusCode?: number }).statusCode === 404
      ? 'Invalid invite code'
      : 'Failed to join organisation'
  } finally {
    busy.value = false
  }
}

async function leaveOrg() {
  if (busy.value) return
  if (!confirm('Leave this organisation? You will lose access to its team-shared content.')) return
  busy.value = true
  error.value = null
  try {
    await $fetch('/api/orgs/leave', {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    await refresh()
  } catch (e: unknown) {
    error.value = (e as { statusCode?: number }).statusCode === 409
      ? 'You are the last admin — promote another member before leaving'
      : 'Failed to leave organisation'
  } finally {
    busy.value = false
  }
}

async function rotateInvite() {
  if (busy.value) return
  busy.value = true
  error.value = null
  try {
    org.value = await $fetch<Org>('/api/orgs/rotate-invite', {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
    })
  } catch {
    error.value = 'Failed to rotate invite code'
  } finally {
    busy.value = false
  }
}

async function setRole(member: OrgMember, role: 'admin' | 'member') {
  if (busy.value) return
  busy.value = true
  error.value = null
  try {
    org.value = await $fetch<Org>(`/api/orgs/members/${member.id}`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: { org_role: role },
    })
  } catch (e: unknown) {
    error.value = (e as { statusCode?: number }).statusCode === 409
      ? 'An organisation must keep at least one admin'
      : 'Failed to update member'
  } finally {
    busy.value = false
  }
}

async function removeMember(member: OrgMember) {
  if (busy.value) return
  if (!confirm(`Remove @${member.handle} from the organisation?`)) return
  busy.value = true
  error.value = null
  try {
    org.value = await $fetch<Org>(`/api/orgs/members/${member.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${auth.token}` },
    })
  } catch {
    error.value = 'Failed to remove member'
  } finally {
    busy.value = false
  }
}

async function copyInvite() {
  if (!org.value?.invite_code) return
  await navigator.clipboard.writeText(org.value.invite_code)
  copied.value = true
  setTimeout(() => { copied.value = false }, 1500)
}

// ── Teams (KC-069, docs/10-teams-and-acls.md) ──────────────────────────────

interface TeamMember {
  id: string
  handle: string
  display_name: string
}

interface TeamSummary {
  id: string
  name: string
  member_count: number
  is_member: boolean
  can_manage: boolean
  created_at: string
}

interface TeamDetail {
  id: string
  name: string
  created_at: string
  can_manage: boolean
  members: TeamMember[]
}

const teams = ref<TeamSummary[]>([])
const newTeamName = ref('')
const expandedTeam = ref<TeamDetail | null>(null)
const teamBusy = ref(false)
const teamError = ref<string | null>(null)
const addMemberId = ref('')

const teamHeaders = () => ({ Authorization: `Bearer ${auth.token}` })

// Org members not yet in the expanded team — candidates for adding
const addableMembers = computed(() => {
  if (!org.value || !expandedTeam.value) return []
  const inTeam = new Set(expandedTeam.value.members.map((m) => m.id))
  return org.value.members.filter((m) => !inTeam.has(m.id))
})

async function loadTeams() {
  if (!org.value) return
  teams.value = await $fetch<TeamSummary[]>('/api/orgs/teams', { headers: teamHeaders() }).catch(() => [])
}

async function createTeam() {
  if (!newTeamName.value.trim() || teamBusy.value) return
  teamBusy.value = true
  teamError.value = null
  try {
    await $fetch('/api/orgs/teams', {
      method: 'POST',
      headers: teamHeaders(),
      body: { name: newTeamName.value.trim() },
    })
    newTeamName.value = ''
    await loadTeams()
  } catch (e: unknown) {
    teamError.value = (e as { statusCode?: number }).statusCode === 409
      ? 'A team with that name already exists'
      : 'Failed to create team'
  } finally {
    teamBusy.value = false
  }
}

async function toggleTeam(team: TeamSummary) {
  teamError.value = null
  if (expandedTeam.value?.id === team.id) {
    expandedTeam.value = null
    return
  }
  expandedTeam.value = await $fetch<TeamDetail>(`/api/orgs/teams/${team.id}`, {
    headers: teamHeaders(),
  }).catch(() => null)
}

async function addTeamMember() {
  if (!expandedTeam.value || !addMemberId.value || teamBusy.value) return
  teamBusy.value = true
  teamError.value = null
  try {
    expandedTeam.value = await $fetch<TeamDetail>(`/api/orgs/teams/${expandedTeam.value.id}/members`, {
      method: 'POST',
      headers: teamHeaders(),
      body: { user_id: addMemberId.value },
    })
    addMemberId.value = ''
    await loadTeams()
  } catch {
    teamError.value = 'Failed to add member'
  } finally {
    teamBusy.value = false
  }
}

async function removeTeamMember(member: TeamMember) {
  if (!expandedTeam.value || teamBusy.value) return
  teamBusy.value = true
  teamError.value = null
  try {
    expandedTeam.value = await $fetch<TeamDetail>(
      `/api/orgs/teams/${expandedTeam.value.id}/members/${member.id}`,
      { method: 'DELETE', headers: teamHeaders() }
    )
    await loadTeams()
  } catch {
    teamError.value = 'Failed to remove member'
  } finally {
    teamBusy.value = false
  }
}

async function deleteTeam(team: TeamSummary) {
  if (teamBusy.value) return
  if (!confirm(`Delete team “${team.name}”? Grants to this team are revoked immediately.`)) return
  teamBusy.value = true
  teamError.value = null
  try {
    await $fetch(`/api/orgs/teams/${team.id}`, { method: 'DELETE', headers: teamHeaders() })
    if (expandedTeam.value?.id === team.id) expandedTeam.value = null
    await loadTeams()
  } catch {
    teamError.value = 'Failed to delete team'
  } finally {
    teamBusy.value = false
  }
}

onMounted(async () => {
  await fetchOrg()
  await loadTeams()
})
</script>

<template>
  <div class="max-w-3xl mx-auto py-10 px-6">
    <header class="mb-8">
      <h1 class="text-2xl font-semibold text-text-primary">Organisation</h1>
      <p class="text-sm text-text-muted mt-0.5">
        Content marked <span class="font-medium">Team</span> is visible to members of your organisation
      </p>
    </header>

    <p v-if="error" class="mb-6 px-4 py-3 rounded-lg text-sm bg-red-50 text-red-700 border border-red-200">
      {{ error }}
    </p>

    <div v-if="loading" class="text-sm text-text-muted">Loading…</div>

    <!-- Org-less: create or join -->
    <div v-else-if="!org" class="grid gap-6 sm:grid-cols-2">
      <section class="p-5 rounded-xl border border-border bg-surface">
        <h2 class="text-sm font-semibold text-text-primary mb-1">Create an organisation</h2>
        <p class="text-xs text-text-muted mb-4">You'll be its admin and can invite others.</p>
        <form class="flex flex-col gap-3" @submit.prevent="createOrg">
          <input
            v-model="newName"
            type="text"
            maxlength="100"
            placeholder="Organisation name"
            class="px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/40"
          >
          <button
            type="submit"
            :disabled="!newName.trim() || busy"
            class="px-3 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            Create
          </button>
        </form>
      </section>

      <section class="p-5 rounded-xl border border-border bg-surface">
        <h2 class="text-sm font-semibold text-text-primary mb-1">Join an organisation</h2>
        <p class="text-xs text-text-muted mb-4">Paste an invite code from an admin.</p>
        <form class="flex flex-col gap-3" @submit.prevent="joinOrg">
          <input
            v-model="joinCode"
            type="text"
            maxlength="36"
            placeholder="Invite code"
            class="px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/40"
          >
          <button
            type="submit"
            :disabled="!joinCode.trim() || busy"
            class="px-3 py-2 rounded-lg text-sm font-medium border border-border text-text-primary hover:bg-surface-secondary transition-colors disabled:opacity-50"
          >
            Join
          </button>
        </form>
      </section>
    </div>

    <!-- Member view -->
    <div v-else class="space-y-6">
      <section class="p-5 rounded-xl border border-border bg-surface flex items-start justify-between gap-4">
        <div>
          <h2 class="text-lg font-semibold text-text-primary">{{ org.name }}</h2>
          <p class="text-xs text-text-muted mt-0.5">
            {{ org.members.length }} member{{ org.members.length === 1 ? '' : 's' }}
            · you are {{ auth.user?.org_role === 'admin' ? 'an admin' : 'a member' }}
          </p>
        </div>
        <button
          :disabled="busy"
          class="px-3 py-1.5 rounded-lg text-xs font-medium border border-border text-text-muted hover:text-red-600 hover:border-red-300 transition-colors disabled:opacity-50"
          @click="leaveOrg"
        >
          Leave
        </button>
      </section>

      <section v-if="isAdmin && org.invite_code" class="p-5 rounded-xl border border-border bg-surface">
        <h3 class="text-sm font-semibold text-text-primary mb-1">Invite code</h3>
        <p class="text-xs text-text-muted mb-3">Anyone with this code can join. Rotate it to revoke.</p>
        <div class="flex items-center gap-2">
          <code class="flex-1 px-3 py-2 rounded-lg bg-surface-secondary border border-border text-sm font-mono text-text-primary truncate">
            {{ org.invite_code }}
          </code>
          <button
            class="px-3 py-2 rounded-lg text-xs font-medium border border-border text-text-primary hover:bg-surface-secondary transition-colors"
            @click="copyInvite"
          >
            {{ copied ? 'Copied ✓' : 'Copy' }}
          </button>
          <button
            :disabled="busy"
            class="px-3 py-2 rounded-lg text-xs font-medium border border-border text-text-muted hover:text-text-primary hover:bg-surface-secondary transition-colors disabled:opacity-50"
            @click="rotateInvite"
          >
            Rotate
          </button>
        </div>
      </section>

      <section class="rounded-xl border border-border bg-surface overflow-hidden">
        <h3 class="text-sm font-semibold text-text-primary px-5 pt-4 pb-2">Members</h3>
        <ul class="divide-y divide-border">
          <li v-for="m in org.members" :key="m.id" class="flex items-center gap-3 px-5 py-3">
            <div class="w-7 h-7 rounded-full bg-accent/10 flex items-center justify-center text-xs font-semibold text-accent shrink-0">
              {{ m.handle.charAt(0).toUpperCase() }}
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm text-text-primary truncate">
                {{ m.display_name }}
                <span v-if="isSelf(m)" class="text-text-muted">(you)</span>
              </p>
              <p class="text-xs text-text-muted truncate">@{{ m.handle }}</p>
            </div>
            <span
              class="px-2 py-0.5 rounded-full text-xs font-medium"
              :class="m.org_role === 'admin' ? 'text-accent bg-accent/10' : 'text-text-muted bg-border'"
            >
              {{ m.org_role }}
            </span>
            <template v-if="isAdmin && !isSelf(m)">
              <button
                v-if="m.org_role === 'member'"
                :disabled="busy"
                class="text-xs text-text-muted hover:text-accent transition-colors disabled:opacity-50"
                @click="setRole(m, 'admin')"
              >
                Promote
              </button>
              <button
                v-else
                :disabled="busy"
                class="text-xs text-text-muted hover:text-accent transition-colors disabled:opacity-50"
                @click="setRole(m, 'member')"
              >
                Demote
              </button>
              <button
                :disabled="busy"
                class="text-xs text-text-muted hover:text-red-600 transition-colors disabled:opacity-50"
                @click="removeMember(m)"
              >
                Remove
              </button>
            </template>
          </li>
        </ul>
      </section>

      <!-- Teams (KC-069) -->
      <section class="rounded-xl border border-border bg-surface overflow-hidden">
        <div class="px-5 pt-4 pb-2">
          <h3 class="text-sm font-semibold text-text-primary">Teams</h3>
          <p class="text-xs text-text-muted mt-0.5">
            Named subsets of this organisation — share KBs, assets, or harnesses with a team from the item's Share dialog.
          </p>
        </div>

        <p v-if="teamError" class="mx-5 mb-2 px-3 py-2 rounded-lg text-xs bg-red-50 text-red-700 border border-red-200">
          {{ teamError }}
        </p>

        <form class="flex gap-2 px-5 pb-3" @submit.prevent="createTeam">
          <input
            v-model="newTeamName"
            type="text"
            maxlength="100"
            placeholder="New team name"
            class="flex-1 px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/40"
          >
          <button
            type="submit"
            :disabled="!newTeamName.trim() || teamBusy"
            class="px-3 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            Create
          </button>
        </form>

        <p v-if="teams.length === 0" class="px-5 pb-4 text-xs text-text-muted">No teams yet.</p>
        <ul v-else class="divide-y divide-border">
          <li v-for="t in teams" :key="t.id">
            <div class="flex items-center gap-3 px-5 py-3">
              <button class="flex-1 min-w-0 text-left" @click="toggleTeam(t)">
                <p class="text-sm text-text-primary truncate">
                  {{ t.name }}
                  <span v-if="t.is_member" class="text-text-muted">(member)</span>
                </p>
                <p class="text-xs text-text-muted">
                  {{ t.member_count }} member{{ t.member_count === 1 ? '' : 's' }}
                </p>
              </button>
              <button
                v-if="t.can_manage"
                :disabled="teamBusy"
                class="text-xs text-text-muted hover:text-red-600 transition-colors disabled:opacity-50"
                @click="deleteTeam(t)"
              >
                Delete
              </button>
              <svg
                class="w-4 h-4 text-text-muted transition-transform"
                :class="expandedTeam?.id === t.id ? 'rotate-180' : ''"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </div>

            <div v-if="expandedTeam?.id === t.id" class="px-5 pb-4 bg-surface-secondary/40">
              <ul class="divide-y divide-border">
                <li v-for="m in expandedTeam.members" :key="m.id" class="flex items-center gap-3 py-2">
                  <div class="w-6 h-6 rounded-full bg-accent/10 flex items-center justify-center text-[10px] font-semibold text-accent shrink-0">
                    {{ m.handle.charAt(0).toUpperCase() }}
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-sm text-text-primary truncate">{{ m.display_name }}</p>
                    <p class="text-xs text-text-muted truncate">@{{ m.handle }}</p>
                  </div>
                  <button
                    v-if="expandedTeam.can_manage || m.id === auth.user?.id"
                    :disabled="teamBusy"
                    class="text-xs text-text-muted hover:text-red-600 transition-colors disabled:opacity-50"
                    @click="removeTeamMember(m)"
                  >
                    {{ m.id === auth.user?.id ? 'Leave' : 'Remove' }}
                  </button>
                </li>
              </ul>

              <form
                v-if="expandedTeam.can_manage && addableMembers.length > 0"
                class="flex gap-2 mt-3"
                @submit.prevent="addTeamMember"
              >
                <select
                  v-model="addMemberId"
                  class="flex-1 px-2 py-1.5 rounded-lg border border-border bg-surface text-xs text-text-primary focus:outline-none focus:border-accent"
                >
                  <option value="" disabled>Add an org member…</option>
                  <option v-for="m in addableMembers" :key="m.id" :value="m.id">
                    {{ m.display_name }} (@{{ m.handle }})
                  </option>
                </select>
                <button
                  type="submit"
                  :disabled="!addMemberId || teamBusy"
                  class="px-3 py-1.5 rounded-lg text-xs font-medium border border-border text-text-primary hover:bg-surface transition-colors disabled:opacity-50"
                >
                  Add
                </button>
              </form>
            </div>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
