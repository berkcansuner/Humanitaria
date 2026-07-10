<template>
  <div ref="host"></div>
</template>

<script setup>
// Thin bridge that mounts the React SuggestionCard island inside this Vue
// component and forwards its callbacks to Vue emits. JSX lives only in the
// .jsx file (handled by @vitejs/plugin-react); here we use React.createElement.
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { createElement } from 'react'
import { createRoot } from 'react-dom/client'
import SuggestionCard from './react/SuggestionCard.jsx'

const props = defineProps({
  clarification: { type: Object, required: true },
})
const emit = defineEmits(['apply', 'dismiss'])

const host = ref(null)
let root = null

function render() {
  if (!root) return
  root.render(
    createElement(SuggestionCard, {
      clarification: props.clarification,
      onApply: (values) => emit('apply', values),
      onDismiss: () => emit('dismiss'),
    }),
  )
}

onMounted(() => {
  root = createRoot(host.value)
  render()
})

// Re-render if the clarification payload is replaced (React preserves the
// component's internal stepper state across re-renders of the same type).
watch(() => props.clarification, render)

onBeforeUnmount(() => {
  if (root) {
    root.unmount()
    root = null
  }
})
</script>
