<script setup lang="ts">
definePageMeta({ layout: 'public' })

const route = useRoute()
const handle = route.params.handle as string

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

interface CuratorProfileOut {
  handle: string
  display_name: string
  board_count: number
  boards: BoardSummary[]
}

// SSR fetch
const { data: profile, error } = await useFetch<CuratorProfileOut>(`/api/u/${handle}`)

useSeoMeta({
  title: () => profile.value ? `${profile.value.display_name} (@${profile.value.handle}) — Knowledge Comms` : 'Curator',
  description: () => profile.value ? `${profile.value.board_count} public boards by @${profile.value.handle}` : '',
})
</script>

<template>
  <div class="max-w-4xl mx-auto px-6 py-12">
    <div v-if="error" class="text-center text-warning text-sm py-20">Curator not found.</div>

    <template v-else-if="profile">
      <!-- Profile header -->
      <div class="flex items-center gap-5 mb-10">
        <div
          class="w-14 h-14 rounded-full bg-accent/10 flex items-center justify-center text-xl font-semibold text-accent shrink-0"
        >
          {{ profile.display_name.charAt(0).toUpperCase() }}
        </div>
        <div>
          <h1 class="text-xl font-semibold text-text-primary">{{ profile.display_name }}</h1>
          <p class="text-sm text-text-muted">@{{ profile.handle }}</p>
          <p class="text-xs text-text-muted mt-0.5">
            {{ profile.board_count }} public board{{ profile.board_count !== 1 ? 's' : '' }}
          </p>
        </div>
      </div>

      <!-- Boards grid -->
      <div v-if="profile.boards.length === 0" class="text-center py-16 text-text-muted text-sm">
        No public boards yet.
      </div>
      <div v-else>
        <h2 class="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-5">
          Published boards
        </h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <NuxtLink
            v-for="board in profile.boards"
            :key="board.id"
            :to="`/board/${board.id}`"
            class="group block rounded-xl border border-border bg-surface p-5 hover:border-accent/40 hover:shadow-sm transition-all"
          >
            <div class="flex items-start justify-between gap-2 mb-2">
              <h3 class="text-sm font-semibold text-text-primary group-hover:text-accent transition-colors line-clamp-2">
                {{ board.title }}
              </h3>
              <span class="shrink-0 text-xs text-text-muted whitespace-nowrap">
                {{ board.fork_count }} forks
              </span>
            </div>
            <p
              v-if="board.ai_summary || board.description"
              class="text-xs text-text-secondary leading-5 line-clamp-2 mb-3"
            >
              {{ board.ai_summary || board.description }}
            </p>
            <p class="text-xs text-text-muted">
              {{ board.item_count }} source{{ board.item_count !== 1 ? 's' : '' }}
            </p>
          </NuxtLink>
        </div>
      </div>
    </template>
  </div>
</template>
