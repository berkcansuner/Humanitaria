<template>
  <!-- A day typed and shown as day.month.year in every browser (a native date input
       follows the browser's locale: "08/25/2026" in US English). The calendar button
       opens the browser's own picker on a hidden native input. -->
  <span :class="['date-field', { invalid, disabled }]">
    <input
      :id="id"
      v-model="text"
      class="date-text"
      type="text"
      inputmode="numeric"
      autocomplete="off"
      :placeholder="t('dateField.placeholder')"
      :disabled="disabled"
      :aria-invalid="invalid ? 'true' : undefined"
      @blur="commit"
      @keydown.enter="commit"
    />
    <button
      type="button"
      class="date-pick"
      :disabled="disabled"
      :aria-label="t('dateField.choose')"
      @click="openPicker"
    >
      <CalendarDays :size="16" aria-hidden="true" />
    </button>
    <input
      ref="native"
      class="date-native"
      type="date"
      tabindex="-1"
      aria-hidden="true"
      :value="modelValue"
      :min="min || undefined"
      :max="max || undefined"
      :disabled="disabled"
      @change="onNative"
    />
  </span>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CalendarDays } from 'lucide-vue-next'
import { isoDate, parseDayMonthYear } from '../utils/isoDate.js'

const props = defineProps({
  modelValue: { type: String, default: '' }, // YYYY-MM-DD, or '' for none
  min: { type: String, default: '' },
  max: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  id: { type: String, default: undefined },
})
const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()

const shown = (iso) => (iso ? isoDate(iso) : '')
const text = ref(shown(props.modelValue))
const invalid = ref(false)
const native = ref(null)

watch(
  () => props.modelValue,
  (iso) => {
    text.value = shown(iso)
    invalid.value = false
  },
)

// A typed day outside [min, max] moves to the nearest bound; text that is not a day
// stays, marked invalid, and the value keeps its last good day.
function commit() {
  const raw = text.value.trim()
  if (!raw) {
    text.value = shown(props.modelValue)
    invalid.value = false
    return
  }
  let iso = parseDayMonthYear(raw)
  if (!iso) {
    invalid.value = true
    return
  }
  if (props.min && iso < props.min) iso = props.min
  if (props.max && iso > props.max) iso = props.max
  invalid.value = false
  text.value = shown(iso)
  if (iso !== props.modelValue) emit('update:modelValue', iso)
}

function onNative(e) {
  if (e.target.value) emit('update:modelValue', e.target.value)
}

function openPicker() {
  const el = native.value
  if (!el) return
  try {
    el.showPicker()
  } catch {
    // An engine without showPicker: the native input takes the click itself.
    el.focus()
    el.click()
  }
}
</script>

<style scoped>
.date-field {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 40px;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-lg);
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.date-field:focus-within {
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}
.date-field.invalid {
  border-color: var(--color-error);
}
.date-text {
  flex: 1;
  min-width: 0;
  padding: 8px 0 8px 12px;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-variant-numeric: tabular-nums;
  color: var(--color-text);
  background: transparent;
  border: none;
  outline: none;
}
.date-text::placeholder {
  color: var(--color-muted);
}
.date-pick {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  margin-right: 2px;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition:
    color 0.15s,
    background-color 0.15s;
}
.date-pick:hover:not(:disabled) {
  color: var(--color-accent);
  background-color: var(--color-surface-container);
}
.date-pick:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}
.disabled .date-text,
.date-pick:disabled {
  color: var(--color-muted);
  cursor: not-allowed;
}
/* Rendered (showPicker needs that) but out of sight, under the button. */
.date-native {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 36px;
  height: 1px;
  padding: 0;
  border: 0;
  opacity: 0;
  pointer-events: none;
}
</style>
