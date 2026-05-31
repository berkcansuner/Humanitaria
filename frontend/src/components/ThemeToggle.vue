<template>
  <button
    type="button"
    class="theme-toggle"
    :aria-label="theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç'"
    :title="theme === 'dark' ? 'Açık tema' : 'Koyu tema'"
    @click="toggle"
  >
    <Sun v-if="theme === 'dark'" :size="18" />
    <Moon v-else :size="18" />
  </button>
</template>

<script setup>
import { ref } from 'vue'
import { Sun, Moon } from 'lucide-vue-next'
import { getInitialTheme, setTheme } from '../utils/theme.js'

const theme = ref(getInitialTheme())

function toggle() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  setTheme(theme.value)
}
</script>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  background-color: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s, border-color 0.2s;
}

.theme-toggle:hover {
  background-color: var(--color-surface-container);
  color: var(--color-accent);
  border-color: var(--color-outline);
}
</style>
