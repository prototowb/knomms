<template>
  <div class="flex h-screen bg-surface-secondary text-text-primary">
    <!-- Sidebar navigation -->
    <aside class="w-56 flex-shrink-0 border-r border-border bg-surface flex flex-col">
      <div class="px-5 py-4 border-b border-border">
        <span class="font-semibold text-sm tracking-tight">Knowledge Commons</span>
      </div>
      <nav class="flex-1 px-3 py-4 space-y-1">
        <NuxtLink
          to="/"
          class="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
          active-class="bg-surface-secondary text-text-primary font-medium"
        >
          Home
        </NuxtLink>
        <NuxtLink
          to="/kb"
          class="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
          active-class="bg-surface-secondary text-text-primary font-medium"
        >
          Knowledge Bases
        </NuxtLink>
        <NuxtLink
          to="/learn"
          class="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
          active-class="bg-surface-secondary text-text-primary font-medium"
        >
          Learn
        </NuxtLink>
        <NuxtLink
          to="/explore"
          class="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-text-secondary hover:text-text-primary hover:bg-surface-secondary transition-colors"
          active-class="bg-surface-secondary text-text-primary font-medium"
        >
          Explore
        </NuxtLink>
      </nav>
    </aside>

    <!-- Main content area -->
    <main class="flex-1 overflow-y-auto">
      <slot />
    </main>
  </div>
</template>
