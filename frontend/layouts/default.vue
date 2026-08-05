<script setup lang="ts">
import { useAuthStore } from '~/stores/auth'

const auth = useAuthStore()

function logout() {
  auth.logout()
  navigateTo('/login')
}
</script>

<template>
  <div class="flex h-screen bg-surface-secondary text-text-primary">
    <!-- Sidebar -->
    <aside class="w-56 flex-shrink-0 border-r border-border bg-surface flex flex-col">
      <div class="px-5 py-4 border-b border-border">
        <NuxtLink to="/" class="font-semibold text-sm tracking-tight text-text-primary hover:text-accent transition-colors">
          Knowledge Comms
        </NuxtLink>
      </div>

      <nav class="flex-1 px-3 py-4 space-y-0.5">
        <NuxtLink
          to="/"
          class="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
          active-class="bg-surface-secondary text-text-primary font-medium"
        >
          <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          Dashboard
        </NuxtLink>

        <NuxtLink
          to="/boards"
          class="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
          active-class="bg-surface-secondary text-text-primary font-medium"
        >
          <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM14 13a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
          </svg>
          My Boards
        </NuxtLink>

        <NuxtLink
          to="/explore"
          class="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
          active-class="bg-surface-secondary text-text-primary font-medium"
        >
          <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" />
          </svg>
          Explore
        </NuxtLink>

        <NuxtLink
          to="/assets"
          class="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
          active-class="bg-surface-secondary text-text-primary font-medium"
        >
          <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          AI Assets
        </NuxtLink>

        <NuxtLink
          to="/harnesses"
          class="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
          active-class="bg-surface-secondary text-text-primary font-medium"
        >
          <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" />
          </svg>
          Harnesses
        </NuxtLink>
      </nav>

      <!-- User section at bottom -->
      <div class="px-3 py-3 border-t border-border">
        <NuxtLink
          v-if="auth.user"
          to="/org"
          class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-surface-secondary transition-colors"
          title="Organisation settings"
        >
          <div class="w-6 h-6 rounded-full bg-accent/10 flex items-center justify-center text-xs font-semibold text-accent shrink-0">
            {{ auth.user.handle.charAt(0).toUpperCase() }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-medium text-text-primary truncate">{{ auth.user.display_name }}</p>
            <p class="text-xs text-text-muted truncate">@{{ auth.user.handle }}</p>
          </div>
        </NuxtLink>
        <button
          class="w-full mt-1 flex items-center gap-2 px-3 py-1.5 rounded-md text-xs text-text-muted hover:text-text-primary hover:bg-surface-secondary transition-colors"
          @click="logout"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Sign out
        </button>
      </div>
    </aside>

    <main class="flex-1 overflow-y-auto">
      <slot />
    </main>
  </div>
</template>
