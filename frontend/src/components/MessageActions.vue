<template>
  <div class="message-actions">
    <button
      type="button"
      class="action-btn"
      :aria-label="copied ? 'Copied' : copyLabel"
      :title="copied ? 'Copied' : copyLabel"
      @click="onCopy"
    >
      <Check v-if="copied" :size="15" />
      <Copy v-else :size="15" />
    </button>
    <button
      v-if="role === 'assistant' && canRegenerate"
      type="button"
      class="action-btn"
      aria-label="Regenerate response"
      @click="$emit('regenerate')"
    >
      <RotateCcw :size="15" />
    </button>
    <button
      v-if="role === 'user'"
      type="button"
      class="action-btn"
      aria-label="Edit message"
      @click="$emit('edit')"
    >
      <Pencil :size="15" />
    </button>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Copy, Check, RotateCcw, Pencil } from 'lucide-vue-next'
import { copyWithSources, referenceEntries } from '../utils/citationCopy.js'

const props = defineProps({
  role: { type: String, required: true },
  content: { type: String, default: '' },
  canRegenerate: { type: Boolean, default: true },
  // The answer's shown sources; copied answers carry them as a reference list.
  sources: { type: Array, default: null },
})

const emit = defineEmits(['copy', 'regenerate', 'edit'])

const copied = ref(false)

const copyLabel = computed(() =>
  referenceEntries(props.sources).length ? 'Copy answer with sources' : 'Copy message',
)

async function onCopy() {
  // Markdown keeps formatting; an answer also takes its numbered Sources list so
  // the [n] markers still resolve once pasted into a brief.
  const ok = await copyWithSources(props.content, props.sources)
  if (!ok) return
  emit('copy')
  copied.value = true
  setTimeout(() => {
    copied.value = false
  }, 1500)
}
</script>

<style scoped>
.message-actions {
  display: flex;
  gap: var(--space-1);
  margin-top: var(--space-2);
  opacity: 0;
  transition: opacity 0.15s;
}

.message-bubble:hover .message-actions,
.message-actions:focus-within {
  opacity: 1;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  transition:
    background-color 0.15s,
    color 0.15s;
}

.action-btn:hover {
  background-color: var(--color-surface-container);
  color: var(--color-accent);
}
</style>
