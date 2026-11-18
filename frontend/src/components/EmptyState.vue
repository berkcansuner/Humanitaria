<template>
  <!-- First contact: say what the product promises (cited answers) and offer
       M&E-shaped starting points, not a generic prompt grid. -->
  <div class="empty-state">
    <div class="empty-inner">
      <h2 class="empty-title">{{ t('chat.empty.title') }}</h2>
      <p class="empty-lede">
        {{ t('chat.empty.lede') }}
      </p>

      <ul class="prompt-list" :aria-label="t('chat.empty.examples')">
        <li v-for="p in prompts" :key="p">
          <button type="button" class="prompt-row" @click="$emit('select', p)">
            <span>{{ p }}</span>
            <ArrowRight :size="15" class="prompt-arrow" aria-hidden="true" />
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowRight } from 'lucide-vue-next'

defineEmits(['select'])

const { t } = useI18n()

// The questions M&E staff and analysts actually bring: figures, displacement,
// access, outbreaks. The index covers every country for the last 12 months.
// Sent as written, so a Turkish prompt gets a Turkish answer.
const prompts = computed(() => ['p1', 'p2', 'p3', 'p4'].map((k) => t(`chat.empty.prompts.${k}`)))
</script>

<style scoped>
.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6) var(--space-4);
}

.empty-inner {
  width: 100%;
  max-width: 560px;
}

.empty-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--color-text);
}

.empty-lede {
  margin: var(--space-2) 0 0;
  max-width: 48ch;
  font-size: 15px;
  line-height: 1.55;
  color: var(--color-text-secondary);
}

.prompt-list {
  list-style: none;
  margin: var(--space-6) 0 0;
  padding: 0;
  border-top: 1px solid var(--color-border);
}

.prompt-list li {
  border-bottom: 1px solid var(--color-border);
}

.prompt-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-3) var(--space-2);
  font-size: var(--text-sm);
  line-height: 1.45;
  text-align: left;
  color: var(--color-text);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background-color 0.15s;
}

.prompt-arrow {
  flex-shrink: 0;
  color: var(--color-muted);
  transition:
    color 0.15s,
    transform 0.15s;
}

.prompt-row:hover {
  background-color: var(--color-surface-container-low);
}

.prompt-row:hover .prompt-arrow {
  color: var(--color-accent);
  transform: translateX(2px);
}

.prompt-row:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .prompt-arrow {
    transition: none;
  }
  .prompt-row:hover .prompt-arrow {
    transform: none;
  }
}
</style>
