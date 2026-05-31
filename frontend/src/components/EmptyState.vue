<template>
  <div class="empty-state">
    <div class="empty-icon">
      <MessagesSquare :size="40" />
    </div>
    <h2 class="empty-title">İnsani yardım belgeleri hakkında sorun</h2>
    <p class="empty-subtitle">Başlamak için bir örnek seçin ya da kendi sorunuzu yazın.</p>
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
import { MessagesSquare } from 'lucide-vue-next'

defineEmits(['select'])

// Örnekler indekslenmiş veri kapsamına (Sudan/Yemen/Ukrayna/Suriye) hizalı.
const prompts = [
  'Sudan\'daki son insani durum nedir?',
  'Yemen\'de gıda güvensizliği hakkında ne biliniyor?',
  'Ukrayna\'da yerinden edilme verileri neler?',
  'Suriye\'de sağlık sektörü ihtiyaçları nelerdir?',
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

.empty-icon {
  color: var(--color-accent);
  opacity: 0.85;
}

.empty-title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text);
}

.empty-subtitle {
  font-size: var(--text-sm);
  color: var(--color-muted);
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
  transition: background-color 0.2s, border-color 0.2s, transform 0.15s;
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
