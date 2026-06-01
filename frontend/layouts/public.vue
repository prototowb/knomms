<template>
  <div class="min-h-screen bg-surface text-text-primary">
    <!-- Top navigation -->
    <header class="border-b border-border bg-surface">
      <div class="max-w-6xl mx-auto px-4 h-14 flex items-center">
        <NuxtLink to="/" class="font-semibold text-text-primary">
          Knowledge Commons
        </NuxtLink>
      </div>
    </header>

    <!-- Page content -->
    <main>
      <slot />
    </main>
  </div>
</template>
