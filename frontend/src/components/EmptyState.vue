<template>
  <div class="empty-state">
    <HelpingHandLogo :size="56" :radius="18" class="empty-logo" />
    <h2 class="empty-title">Ask about humanitarian aid</h2>
    <div class="prompt-grid">
      <button
        v-for="(p, i) in prompts"
        :key="i"
        type="button"
        class="prompt-card"
        @click="$emit('select', p)"
      >
        {{ p }}
      </button>
    </div>
  </div>
</template>

<script setup>
import HelpingHandLogo from './HelpingHandLogo.vue'

defineEmits(['select'])

// Örnekler indekslenmiş veri kapsamına (Sudan/Yemen/Ukrayna/Suriye) hizalı.
const prompts = [
  'What is the current humanitarian situation in Sudan?',
  'What is known about food insecurity in Yemen?',
  'What are the displacement figures in Ukraine?',
  'What are the health sector needs in Syria?',
]
</script>

<style scoped>
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-6) var(--space-4);
  gap: var(--space-3);
}

.empty-logo {
  margin-bottom: var(--space-1);
}

.empty-title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-2);
}

.prompt-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  width: 100%;
  max-width: 560px;
}

.prompt-card {
  text-align: left;
  padding: var(--space-3) var(--space-4);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-text);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition:
    background-color 0.2s,
    border-color 0.2s,
    transform 0.15s;
}

.prompt-card:hover {
  background-color: var(--color-surface-container);
  border-color: var(--color-outline);
  transform: translateY(-1px);
}

@media (max-width: 640px) {
  .prompt-grid {
    grid-template-columns: 1fr;
  }
}
</style>
