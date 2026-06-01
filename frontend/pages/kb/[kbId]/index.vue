<script setup lang="ts">
import { ref } from 'vue'
import { useStreamingQuery } from '~/composables/useStreamingQuery'

const route = useRoute()
const kbId = route.params.kbId as string

const queryText = ref('')
const { response, citations, isStreaming, error, submit } = useStreamingQuery(kbId, queryText.value)

async function handleSubmit() {
  if (!queryText.value.trim() || isStreaming.value) return
  await submit()
}
</script>

<template>
  <div class="flex flex-col h-full p-8">
    <h1 class="text-xl font-semibold text-text-primary mb-6">
      Knowledge Base
      <span class="ml-2 text-text-muted font-normal text-sm">{{ kbId }}</span>
    </h1>

    <!-- Response area -->
    <div class="flex-1 overflow-y-auto mb-6 rounded-lg border border-border bg-surface p-5 min-h-[200px]">
      <p v-if="error" class="text-warning text-sm">{{ error }}</p>
      <p v-else-if="!response" class="text-text-muted text-sm">
        Ask a question to get started.
      </p>
      <div v-else class="font-prose text-text-primary whitespace-pre-wrap text-sm leading-relaxed">
        {{ response }}
        <span v-if="isStreaming" class="inline-block w-1.5 h-4 bg-accent animate-pulse align-middle ml-0.5" />
      </div>
    </div>

    <!-- Chat input -->
    <form class="flex gap-3" @submit.prevent="handleSubmit">
      <input
        v-model="queryText"
        type="text"
        placeholder="Ask a question..."
        :disabled="isStreaming"
        class="flex-1 border border-border rounded-lg px-4 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50"
      />
      <button
        type="submit"
        :disabled="isStreaming || !queryText.trim()"
        class="px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {{ isStreaming ? 'Thinking...' : 'Ask' }}
      </button>
    </form>
  </div>
</template>
