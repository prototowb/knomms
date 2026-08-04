<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelPin: string
  deprecated?: boolean
}>()

const family = computed(() => props.modelPin.split(':')[0])
const tag = computed(() => {
  const parts = props.modelPin.split(':')
  return parts.length > 1 ? parts.slice(1).join(':') : null
})
</script>

<template>
  <span
    class="inline-flex items-center text-xs font-mono rounded border overflow-hidden"
    :class="deprecated ? 'border-warning/40' : 'border-border'"
  >
    <span
      class="px-1.5 py-0.5 bg-surface-secondary"
      :class="deprecated ? 'text-warning' : 'text-text-secondary'"
    >{{ family }}</span>
    <span
      v-if="tag"
      class="px-1.5 py-0.5 border-l"
      :class="deprecated
        ? 'border-warning/40 bg-warning/10 text-warning'
        : 'border-border bg-surface text-text-muted'"
    >{{ tag }}</span>
  </span>
</template>
