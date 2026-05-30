<template>
  <div class="suggestion-card" v-if="steps.length">
    <div class="sc-header">
      <span class="sc-title">{{ steps[current].title }}</span>
      <div class="sc-nav">
        <button class="sc-iconbtn" :disabled="current === 0" @click="prev" aria-label="Önceki">
          <ChevronLeft :size="16" />
        </button>
        <span class="sc-pager">{{ current + 1 }} / {{ steps.length }}</span>
        <button class="sc-iconbtn" @click="skip" aria-label="Sonraki">
          <ChevronRight :size="16" />
        </button>
        <button class="sc-iconbtn" @click="$emit('dismiss')" aria-label="Kapat">
          <X :size="16" />
        </button>
      </div>
    </div>

    <ul class="sc-options">
      <li v-for="(opt, i) in steps[current].options" :key="opt"
          class="sc-option" :class="{ selected: selections[steps[current].key] === opt }"
          @click="select(opt)">
        <span class="sc-num">{{ i + 1 }}</span>
        <span class="sc-label">{{ opt }}</span>
        <ArrowRight :size="16" class="sc-arrow" />
      </li>
    </ul>

    <div class="sc-footer">
      <button class="sc-skip" @click="skip">{{ isLast ? 'Bitir' : 'Atla' }}</button>
      <button class="sc-reply" @click="$emit('dismiss')">veya doğrudan yazın</button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ChevronLeft, ChevronRight, ArrowRight, X } from 'lucide-vue-next'

const props = defineProps({
  clarification: { type: Object, required: true },
})
const emit = defineEmits(['apply', 'dismiss'])

// Each missing dimension becomes one step (only those with suggestions).
const STEP_DEFS = [
  { key: 'country', src: 'countries', title: 'Hangi ülke hakkında bilgi almak istiyorsunuz?' },
  { key: 'date', src: 'time_periods', title: 'Hangi zaman aralığı?' },
  { key: 'theme', src: 'themes', title: 'Hangi konu?' },
]

const steps = computed(() => {
  const s = props.clarification?.suggestions || {}
  return STEP_DEFS
    .filter(d => Array.isArray(s[d.src]) && s[d.src].length)
    .map(d => ({ key: d.key, title: d.title, options: s[d.src] }))
})

const current = ref(0)
const selections = reactive({})
const isLast = computed(() => current.value >= steps.value.length - 1)

function advance() {
  if (current.value < steps.value.length - 1) current.value++
  else finalize()
}
function select(opt) {
  selections[steps.value[current.value].key] = opt
  advance()
}
function skip() {
  advance()
}
function prev() {
  if (current.value > 0) current.value--
}
function finalize() {
  // Collect chosen values in step order and let the parent refine + re-send.
  const values = steps.value.map(s => selections[s.key]).filter(Boolean)
  if (values.length) emit('apply', values)
  else emit('dismiss')
}
</script>

<style scoped>
.suggestion-card {
  margin-top: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  overflow: hidden;
}

.sc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.sc-title {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-text);
}

.sc-nav {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex-shrink: 0;
}

.sc-pager {
  font-size: var(--text-xs);
  color: var(--color-muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.sc-iconbtn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  cursor: pointer;
  transition: color 0.15s, background-color 0.15s;
}

.sc-iconbtn:hover:not(:disabled) {
  color: var(--color-accent);
  background: var(--color-surface-container-low);
}

.sc-iconbtn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sc-options {
  list-style: none;
  margin: 0;
  padding: var(--space-2);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sc-option {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color 0.15s;
}

.sc-option:hover,
.sc-option.selected {
  background: var(--color-surface-container-low);
}

.sc-num {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-muted);
  background: var(--color-surface-container);
  border-radius: var(--radius-sm);
}

.sc-label {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--color-text);
}

.sc-arrow {
  flex-shrink: 0;
  color: var(--color-muted);
  opacity: 0;
  transition: opacity 0.15s, color 0.15s;
}

.sc-option:hover .sc-arrow {
  opacity: 1;
  color: var(--color-accent);
}

.sc-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-1) var(--space-4) var(--space-3);
}

.sc-skip {
  background: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  padding: var(--space-1) var(--space-4);
  font-family: var(--font-body);
  font-size: var(--text-xs);
  color: var(--color-text);
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}

.sc-skip:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.sc-reply {
  background: none;
  border: none;
  font-family: var(--font-body);
  font-size: var(--text-xs);
  color: var(--color-muted);
  cursor: pointer;
  text-decoration: underline;
}

.sc-reply:hover {
  color: var(--color-accent);
}
</style>
