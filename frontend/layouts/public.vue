<script setup lang="ts">
const auth = useAuthStore()
</script>

<template>
  <div class="min-h-screen bg-surface text-text-primary">
    <!-- Top navigation -->
    <header class="border-b border-border bg-surface">
      <div class="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <NuxtLink to="/" class="font-semibold text-text-primary">
          Knowledge Commons
        </NuxtLink>

        <ClientOnly>
          <nav v-if="auth.isLoggedIn" class="flex items-center gap-4">
            <NuxtLink
              to="/"
              class="text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              Dashboard
            </NuxtLink>
            <NuxtLink
              to="/explore"
              class="text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              Explore
            </NuxtLink>
          </nav>
          <nav v-else class="flex items-center gap-3">
            <NuxtLink
              to="/login"
              class="text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              Log in
            </NuxtLink>
            <NuxtLink
              to="/register"
              class="text-sm font-medium px-3 py-1.5 rounded-lg bg-accent text-white hover:bg-accent-hover transition-colors"
            >
              Sign up
            </NuxtLink>
          </nav>
        </ClientOnly>
      </div>
    </header>

    <!-- Page content -->
    <main>
      <slot />
    </main>
  </div>
</template>
