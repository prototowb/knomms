<script setup lang="ts">
import { ref, computed } from 'vue'
import { useStreamingQuery } from '~/composables/useStreamingQuery'

const route = useRoute()
const kbId = route.params.kbId as string

const queryText = ref('')
const { response, citations, isStreaming, error, submit } = useStreamingQuery(kbId)

const citationList = computed(() =>
  Object.values(citations.value) as Array<{
    chunk_id: string
    source_id: string
    locator: string
    excerpt: string
  }>
)

const hasCitations = computed(() => citationList.value.length > 0)

async function handleSubmit() {
  if (!queryText.value.trim() || isStreaming.value) return
  await submit(queryText.value)
}

function formatResponse(text: string) {
  // Replace [SOURCE:id] markers with styled spans
  return text.replace(
    /\[SOURCE:([a-f0-9-]{36})\]/g,
    '<sup class="citation-ref text-grounded font-mono text-xs cursor-pointer hover:underline" data-id="$1">[src]</sup>'
  )
}
</script>

<template>
  <div class="flex h-full overflow-hidden bg-surface">
    <!-- Main Q&A column -->
    <div class="flex flex-col flex-1 min-w-0 p-6">
      <header class="mb-5 flex items-center gap-3">
        <div>
          <h1 class="text-lg font-semibold text-text-primary">Knowledge Base</h1>
          <p class="text-xs text-text-muted font-mono mt-0.5">{{ kbId }}</p>
        </div>
        <div class="ml-auto">
          <NuxtLink
            :to="`/kb/${kbId}/learn`"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-grounded text-white hover:bg-green-700 transition-colors"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            Learning paths
          </NuxtLink>
        </div>
      </header>

      <!-- Response area -->
      <div
        class="flex-1 overflow-y-auto rounded-xl border border-border bg-surface-secondary p-5 min-h-[180px] mb-5"
      >
        <p v-if="error" class="text-warning text-sm">{{ error }}</p>
        <p v-else-if="!response && !isStreaming" class="text-text-muted text-sm">
          Ask a question grounded in this knowledge base.
        </p>
        <div
          v-else
          class="font-prose text-text-primary text-sm leading-7"
          v-html="formatResponse(response)"
        />
        <span
          v-if="isStreaming"
          class="inline-block w-1.5 h-4 bg-accent animate-pulse align-middle ml-0.5"
        />
      </div>

      <!-- Input -->
      <form class="flex gap-3" @submit.prevent="handleSubmit">
        <input
          v-model="queryText"
          type="text"
          placeholder="Ask a question..."
          :disabled="isStreaming"
          class="flex-1 border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50 transition-colors"
        />
        <button
          type="submit"
          :disabled="isStreaming || !queryText.trim()"
          class="px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ isStreaming ? 'Thinking…' : 'Ask' }}
        </button>
      </form>
    </div>

    <!-- Citation sidebar -->
    <aside
      v-if="hasCitations"
      class="w-72 shrink-0 border-l border-border bg-surface overflow-y-auto p-4"
    >
      <h2 class="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
        Sources ({{ citationList.length }})
      </h2>
      <ul class="space-y-3">
        <li
          v-for="c in citationList"
          :key="c.chunk_id"
          class="rounded-lg border border-grounded/20 bg-grounded-light p-3"
        >
          <p class="text-xs font-mono text-grounded mb-1">{{ c.locator }}</p>
          <p class="text-xs text-text-secondary leading-5 line-clamp-4">{{ c.excerpt }}</p>
        </li>
      </ul>
    </aside>
  </div>
</template>
