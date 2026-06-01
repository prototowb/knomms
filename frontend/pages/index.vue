<script setup lang="ts">
import { useAuthStore } from '~/stores/auth'

const authStore = useAuthStore()

// Redirect unauthenticated users to the public discovery page
if (!authStore.isLoggedIn) {
  await navigateTo('/explore')
}
</script>

<template>
  <div class="p-8">
    <h1 class="text-2xl font-semibold text-text-primary mb-6">Your Knowledge Bases</h1>

    <!-- Dashboard stub -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div class="border border-border rounded-lg p-5 bg-surface hover:border-border-strong transition-colors cursor-pointer">
        <p class="text-text-muted text-sm">No knowledge bases yet.</p>
        <button class="mt-3 text-sm text-accent hover:text-accent-hover font-medium">
          + Create your first KB
        </button>
      </div>
    </div>
  </div>
</template>
