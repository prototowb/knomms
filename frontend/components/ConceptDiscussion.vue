<script setup lang="ts">
// Passage-anchored discussion on a path concept (KC-084, docs/13).
// Visible to whoever can read the path; the path owner moderates via delete.
import { ref, watch } from 'vue'
import { useAuthStore } from '~/stores/auth'

interface Author { id: string; handle: string; display_name: string }

interface SourcePassage {
  chunk_id: string
  locator: string
  source_id: string
  excerpt: string
}

interface ThreadSummary {
  id: string
  concept_id: string
  title: string
  body: string
  passage_chunk_id: string | null
  passage_excerpt: string
  author: Author | null
  post_count: number
  created_at: string
}

interface Post {
  id: string
  thread_id: string
  body: string
  author: Author | null
  created_at: string
}

interface Thread extends ThreadSummary {
  posts: Post[]
}

const props = defineProps<{
  pathId: string
  conceptId: string
  sourcePassages: SourcePassage[]
  isPathOwner: boolean
}>()

const auth = useAuthStore()

const threads = ref<ThreadSummary[]>([])
const loaded = ref(false)
const loadError = ref<string | null>(null)

const openThread = ref<Thread | null>(null)
const threadLoading = ref(false)

const showNewForm = ref(false)
const newTitle = ref('')
const newBody = ref('')
const newAnchor = ref<string>('')  // '' = no anchor
const creating = ref(false)
const createError = ref<string | null>(null)

const replyBody = ref('')
const replying = ref(false)
const deleting = ref<Record<string, boolean>>({})

async function loadThreads() {
  try {
    threads.value = await $fetch<ThreadSummary[]>(
      `/api/learning-paths/${props.pathId}/concepts/${props.conceptId}/threads`,
      { headers: { Authorization: `Bearer ${auth.token}` } }
    )
    loadError.value = null
  } catch {
    loadError.value = 'Could not load discussion.'
  } finally {
    loaded.value = true
  }
}

async function openThreadView(threadId: string) {
  threadLoading.value = true
  try {
    openThread.value = await $fetch<Thread>(
      `/api/learning-paths/${props.pathId}/threads/${threadId}`,
      { headers: { Authorization: `Bearer ${auth.token}` } }
    )
  } catch {
    loadError.value = 'Could not load the thread.'
  } finally {
    threadLoading.value = false
  }
}

function closeThreadView() {
  openThread.value = null
  replyBody.value = ''
  loadThreads()
}

async function createThread() {
  if (!newTitle.value.trim() || creating.value) return
  creating.value = true
  createError.value = null
  try {
    const thread = await $fetch<Thread>(
      `/api/learning-paths/${props.pathId}/concepts/${props.conceptId}/threads`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${auth.token}` },
        body: {
          title: newTitle.value,
          body: newBody.value,
          passage_chunk_id: newAnchor.value || null,
        },
      }
    )
    newTitle.value = ''
    newBody.value = ''
    newAnchor.value = ''
    showNewForm.value = false
    await loadThreads()
    openThread.value = thread
  } catch {
    createError.value = 'Could not create the thread.'
  } finally {
    creating.value = false
  }
}

async function submitReply() {
  if (!replyBody.value.trim() || replying.value || !openThread.value) return
  replying.value = true
  try {
    const post = await $fetch<Post>(
      `/api/learning-paths/${props.pathId}/threads/${openThread.value.id}/posts`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${auth.token}` },
        body: { body: replyBody.value },
      }
    )
    openThread.value.posts.push(post)
    openThread.value.post_count += 1
    replyBody.value = ''
  } catch {
    // keep the draft; the user can retry
  } finally {
    replying.value = false
  }
}

function canDelete(post: Post): boolean {
  return props.isPathOwner || post.author?.id === auth.user?.id
}

async function deletePost(post: Post) {
  if (deleting.value[post.id] || !openThread.value) return
  deleting.value[post.id] = true
  try {
    // Cast to plain string — Nuxt's typed $fetch doesn't infer DELETE for
    // this dynamic route and rejects the method otherwise.
    await $fetch(
      `/api/learning-paths/${props.pathId}/threads/${openThread.value.id}/posts/${post.id}` as string,
      { method: 'DELETE', headers: { Authorization: `Bearer ${auth.token}` } }
    )
    openThread.value.posts = openThread.value.posts.filter(p => p.id !== post.id)
    openThread.value.post_count -= 1
  } catch {
    // post stays; the user can retry
  } finally {
    deleting.value[post.id] = false
  }
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

// Reload when the visible concept changes; reset any open thread
watch(
  () => props.conceptId,
  () => {
    openThread.value = null
    loaded.value = false
    loadThreads()
  },
  { immediate: true },
)
</script>

<template>
  <div class="rounded-xl border border-border bg-surface p-4">
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs font-semibold text-text-secondary uppercase tracking-wider">
        Discussion
        <span v-if="loaded" class="text-text-muted font-normal normal-case">· {{ threads.length }} thread{{ threads.length !== 1 ? 's' : '' }}</span>
      </p>
      <button
        v-if="!openThread"
        class="text-xs px-3 py-1.5 rounded-lg border border-border text-text-secondary hover:bg-surface-secondary transition-colors"
        @click="showNewForm = !showNewForm"
      >
        {{ showNewForm ? 'Cancel' : '+ New thread' }}
      </button>
      <button
        v-else
        class="text-xs text-text-muted hover:text-accent"
        @click="closeThreadView"
      >
        ← All threads
      </button>
    </div>

    <p v-if="loadError" class="text-xs text-warning mb-2">{{ loadError }}</p>

    <!-- New thread form -->
    <div v-if="showNewForm && !openThread" class="rounded-lg border border-border p-3 mb-3 space-y-2">
      <input
        v-model="newTitle"
        type="text"
        placeholder="What's your question or observation?"
        class="w-full border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
      />
      <textarea
        v-model="newBody"
        rows="2"
        placeholder="Add detail (optional)…"
        class="w-full border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent resize-none"
      />
      <select
        v-if="sourcePassages.length > 0"
        v-model="newAnchor"
        class="w-full border border-border rounded-lg px-3 py-2 text-xs text-text-secondary bg-surface focus:outline-none focus:border-accent"
      >
        <option value="">No passage anchor</option>
        <option v-for="p in sourcePassages" :key="p.chunk_id" :value="p.chunk_id">
          {{ p.locator }} — {{ p.excerpt.slice(0, 80) }}{{ p.excerpt.length > 80 ? '…' : '' }}
        </option>
      </select>
      <p v-if="createError" class="text-xs text-warning">{{ createError }}</p>
      <div class="flex justify-end">
        <button
          :disabled="!newTitle.trim() || creating"
          class="text-xs px-4 py-2 rounded-lg bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
          @click="createThread"
        >
          {{ creating ? 'Posting…' : 'Post thread' }}
        </button>
      </div>
    </div>

    <!-- Thread view -->
    <div v-if="openThread">
      <div class="mb-3">
        <p class="text-sm font-medium text-text-primary">{{ openThread.title }}</p>
        <p class="text-xs text-text-muted mt-0.5">
          {{ openThread.author ? `@${openThread.author.handle}` : '—' }} · {{ fmtDate(openThread.created_at) }}
        </p>
        <div v-if="openThread.passage_excerpt" class="rounded-lg border border-grounded/20 bg-grounded-light p-2 mt-2">
          <p class="text-xs text-text-secondary leading-5">“{{ openThread.passage_excerpt }}”</p>
        </div>
        <p v-if="openThread.body" class="text-sm text-text-secondary leading-6 mt-2">{{ openThread.body }}</p>
      </div>

      <div v-if="openThread.posts.length > 0" class="space-y-2 mb-3">
        <div v-for="post in openThread.posts" :key="post.id" class="rounded-lg bg-surface-secondary border border-border px-3 py-2">
          <div class="flex items-center justify-between">
            <p class="text-xs text-text-muted">
              {{ post.author ? `@${post.author.handle}` : '—' }} · {{ fmtDate(post.created_at) }}
            </p>
            <button
              v-if="canDelete(post)"
              :disabled="deleting[post.id]"
              class="text-xs text-text-muted hover:text-warning disabled:opacity-50"
              title="Delete post"
              @click="deletePost(post)"
            >
              Delete
            </button>
          </div>
          <p class="text-sm text-text-primary leading-6 mt-1 whitespace-pre-wrap">{{ post.body }}</p>
        </div>
      </div>
      <p v-else class="text-xs text-text-muted mb-3">No replies yet.</p>

      <div class="flex gap-2">
        <input
          v-model="replyBody"
          type="text"
          placeholder="Reply…"
          class="flex-1 border border-border rounded-lg px-3 py-2 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
          @keyup.enter="submitReply"
        />
        <button
          :disabled="!replyBody.trim() || replying"
          class="text-xs px-4 py-2 rounded-lg bg-accent text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
          @click="submitReply"
        >
          {{ replying ? '…' : 'Reply' }}
        </button>
      </div>
    </div>

    <!-- Thread list -->
    <template v-else>
      <div v-if="threads.length > 0" class="space-y-2">
        <button
          v-for="t in threads"
          :key="t.id"
          class="w-full text-left rounded-lg border border-border px-3 py-2 hover:border-accent/40 hover:bg-surface-secondary transition-colors"
          @click="openThreadView(t.id)"
        >
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm text-text-primary font-medium truncate">{{ t.title }}</p>
            <span class="text-xs text-text-muted shrink-0">{{ t.post_count }} repl{{ t.post_count === 1 ? 'y' : 'ies' }}</span>
          </div>
          <p v-if="t.passage_excerpt" class="text-xs text-grounded truncate mt-0.5">“{{ t.passage_excerpt }}”</p>
          <p class="text-xs text-text-muted mt-0.5">
            {{ t.author ? `@${t.author.handle}` : '—' }} · {{ fmtDate(t.created_at) }}
          </p>
        </button>
      </div>
      <p v-else-if="loaded && !showNewForm" class="text-xs text-text-muted">
        No discussion yet — open a thread, optionally anchored to a source passage.
      </p>
    </template>
  </div>
</template>
