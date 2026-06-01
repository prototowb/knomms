<script setup lang="ts">
definePageMeta({ layout: 'public' })
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <h1 class="text-3xl font-semibold text-text-primary mb-2">
      Discover Knowledge Collections
    </h1>
    <p class="text-text-secondary mb-8">
      Browse publicly shared knowledge boards curated by the community.
    </p>

    <!-- Search -->
    <div class="mb-8">
      <input
        type="search"
        placeholder="Search collections..."
        class="w-full max-w-md border border-border rounded-lg px-4 py-2 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent"
      />
    </div>

    <!-- Placeholder grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="n in 6"
        :key="n"
        class="border border-border rounded-lg p-5 bg-surface animate-pulse"
      >
        <div class="h-4 bg-surface-secondary rounded w-3/4 mb-3" />
        <div class="h-3 bg-surface-secondary rounded w-full mb-2" />
        <div class="h-3 bg-surface-secondary rounded w-2/3" />
      </div>
    </div>
  </div>
</template>
