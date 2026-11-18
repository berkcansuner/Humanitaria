<template>
  <!-- One live region that is always in the DOM, so screen readers announce each
       message. Floats bottom-left, next to the sidebar lists where deletes start. -->
  <div class="toast-region" role="status" aria-live="polite">
    <div v-if="message" :class="['toast', { 'toast-error': kind === 'error' }]">
      <AlertCircle v-if="kind === 'error'" :size="16" class="toast-icon" aria-hidden="true" />
      <span class="toast-text">{{ message }}</span>
      <button
        v-if="actionLabel"
        ref="actionBtn"
        type="button"
        class="toast-action"
        @click="$emit('action')"
      >
        {{ actionLabel }}
      </button>
      <button
        v-else
        type="button"
        class="toast-dismiss"
        :aria-label="t('common.dismiss')"
        @click="$emit('dismiss')"
      >
        <X :size="15" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertCircle, X } from 'lucide-vue-next'

const props = defineProps({
  message: { type: String, default: '' },
  // 'undo' (neutral, with an action) or 'error'.
  kind: { type: String, default: 'undo' },
  actionLabel: { type: String, default: '' },
  // Move focus to the action when the toast opens. The delete button that
  // triggered it has just left the DOM, so this keeps keyboard users in place.
  focusAction: { type: Boolean, default: false },
  // Changes for every new toast (e.g. the pending item's id), so a second delete
  // with the same message still moves focus.
  focusKey: { type: [String, Number], default: null },
})
defineEmits(['action', 'dismiss'])

const { t } = useI18n()

const actionBtn = ref(null)
watch(
  () => [props.message, props.focusKey],
  ([msg]) => {
    if (msg && props.focusAction) nextTick(() => actionBtn.value?.focus())
  },
)
</script>

<style scoped>
.toast-region {
  position: fixed;
  left: var(--space-4);
  bottom: var(--space-4);
  z-index: 60;
  max-width: min(360px, calc(100vw - 2 * var(--space-4)));
}

.toast {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px 10px 10px var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  animation: toast-in 0.18s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-error {
  color: var(--color-error-accent);
  background-color: var(--color-error-bg);
  border-color: color-mix(in oklch, var(--color-error) 35%, transparent);
}

.toast-icon {
  flex-shrink: 0;
}

.toast-text {
  flex: 1;
  min-width: 0;
}

.toast-action {
  flex-shrink: 0;
  padding: 4px var(--space-2);
  font: inherit;
  font-weight: 600;
  color: var(--color-accent);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.toast-action:hover {
  background-color: var(--color-accent-soft);
}

.toast-dismiss {
  flex-shrink: 0;
  display: inline-flex;
  padding: 4px;
  color: inherit;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.toast-action:focus-visible,
.toast-dismiss:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .toast {
    animation: none;
  }
}
</style>
