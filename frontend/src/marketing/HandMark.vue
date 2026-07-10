<template>
  <span
    class="mark"
    :class="{ solid }"
    :style="{ width: size + 'px', height: size + 'px', borderRadius: radius + 'px' }"
  >
    <svg
      :width="icon"
      :height="icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      :stroke-width="stroke"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path v-for="(d, i) in paths" :key="i" :d="d" />
    </svg>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: { type: Number, default: 34 },
  radius: { type: Number, default: 11 },
  stroke: { type: Number, default: 1.6 },
  solid: { type: Boolean, default: false },
})

const icon = computed(() => Math.round(props.size * 0.56))
const paths = [
  'M11 14h2a2 2 0 0 0 0-4h-3c-.6 0-1.1.2-1.4.6L3 16',
  'm7 20 1.6-1.4c.3-.4.8-.6 1.4-.6h4c1.1 0 2.1-.4 2.8-1.2l4.6-4.4a2 2 0 0 0-2.75-2.91l-4.2 3.9',
  'm2 15 6 6',
  'M19.5 9.5c.9-.9 1.5-1.6 1.5-2.7A2.3 2.3 0 0 0 18.7 4.5c-.9 0-1.4.4-1.9.9-.5-.5-1-.9-1.9-.9a2.3 2.3 0 0 0-2.3 2.3c0 1.1.6 1.8 1.5 2.7L16.8 12z',
]
</script>
