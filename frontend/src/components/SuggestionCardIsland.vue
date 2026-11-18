<template>
  <div ref="host"></div>
</template>

<script setup>
// Thin bridge that mounts the React SuggestionCard island inside this Vue
// component and forwards its callbacks to Vue emits. JSX lives only in the
// .jsx file (handled by @vitejs/plugin-react); here we use React.createElement.
// React has no i18n of its own: every string is read here with t() and passed
// in as `labels`, and the island re-renders when the language changes.
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { createElement } from 'react'
import { createRoot } from 'react-dom/client'
import SuggestionCard from './react/SuggestionCard.jsx'

const props = defineProps({
  clarification: { type: Object, required: true },
})
const emit = defineEmits(['apply', 'dismiss'])

const { t, locale } = useI18n()
const host = ref(null)
let root = null

function step(key) {
  return {
    title: t(`chat.suggest.${key}.title`),
    placeholder: t(`chat.suggest.${key}.placeholder`),
  }
}

function labels() {
  return {
    card: t('chat.suggest.card'),
    prev: t('chat.suggest.prev'),
    next: t('chat.suggest.next'),
    close: t('chat.suggest.close'),
    use: t('chat.suggest.use'),
    finish: t('chat.suggest.finish'),
    skip: t('chat.suggest.skip'),
    steps: { country: step('country'), date: step('date'), theme: step('theme') },
  }
}

function render() {
  if (!root) return
  root.render(
    createElement(SuggestionCard, {
      clarification: props.clarification,
      labels: labels(),
      onApply: (values) => emit('apply', values),
      onDismiss: () => emit('dismiss'),
    }),
  )
}

onMounted(() => {
  root = createRoot(host.value)
  render()
})

// Re-render if the clarification payload is replaced or the language changes
// (React preserves the component's internal stepper state across re-renders of
// the same type, so a switch keeps the step and any typed text).
watch([() => props.clarification, locale], render)

onBeforeUnmount(() => {
  if (root) {
    root.unmount()
    root = null
  }
})
</script>
