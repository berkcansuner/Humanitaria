<template>
  <div class="modal" :class="{ open }" :aria-hidden="!open">
    <div class="modal-backdrop" @click="$emit('close')"></div>
    <div class="modal-card" role="dialog" aria-modal="true" aria-label="Sample answer">
      <button ref="closeBtn" class="modal-x" aria-label="Close" @click="$emit('close')">
        <svg
          width="17"
          height="17"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
      <div class="modal-head">
        <HandMark :size="28" :radius="8" :stroke="1.7" solid />
        <div>
          <div class="mh-title">Humanitaria</div>
        </div>
      </div>
      <div class="modal-body">
        <div class="q">What's the latest humanitarian situation in Sudan?</div>
        <div class="a">
          <h4>Sudan — current situation</h4>
          <p>
            Sudan is facing one of the world's largest displacement crises, with
            <strong>millions forced from their homes</strong> since April 2023 — most displaced
            inside the country, and many seeking refuge across borders<span class="cite">1</span>.
          </p>
          <p>
            Food insecurity has deteriorated sharply. Market collapse and disrupted farming have
            pushed several regions to <strong>critical levels of acute food insecurity</strong>,
            with famine conditions confirmed in some areas<span class="cite">2</span>.
          </p>
          <p>The health system is under severe strain:</p>
          <ul>
            <li>
              A large share of health facilities are partly or fully out of service<span
                class="cite"
                >3</span
              >
            </li>
            <li>Outbreaks of cholera and malaria are on the rise<span class="cite">3</span></li>
            <li>Supplies of medicine and essentials are limited<span class="cite">2</span></li>
          </ul>
          <p>
            Humanitarian access remains difficult in many areas due to insecurity and bureaucratic
            constraints<span class="cite">1</span>.
          </p>
          <div class="src">
            <div class="src-h">Sources (3)</div>
            <div class="src-item">
              <span class="n">[1]</span
              ><span
                ><span class="t">Sudan Situation Report</span>
                <span class="m">· OCHA · 12 Mar 2025</span></span
              >
            </div>
            <div class="src-item">
              <span class="n">[2]</span
              ><span
                ><span class="t">Acute Food Insecurity Snapshot</span>
                <span class="m">· IPC · 20 Dec 2024</span></span
              >
            </div>
            <div class="src-item">
              <span class="n">[3]</span
              ><span
                ><span class="t">Sudan Health Cluster Bulletin</span>
                <span class="m">· WHO · 28 Feb 2025</span></span
              >
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onUnmounted } from 'vue'
import HandMark from './HandMark.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const closeBtn = ref(null)
let lastFocused = null

function onKey(e) {
  if (e.key === 'Escape') emit('close')
  // The dialog's only focusable is the close button, so keep Tab inside it.
  else if (e.key === 'Tab') {
    e.preventDefault()
    closeBtn.value?.focus()
  }
}

watch(
  () => props.open,
  (isOpen) => {
    document.body.style.overflow = isOpen ? 'hidden' : ''
    if (isOpen) {
      lastFocused = document.activeElement
      document.addEventListener('keydown', onKey)
      nextTick(() => closeBtn.value?.focus())
    } else {
      document.removeEventListener('keydown', onKey)
      lastFocused?.focus?.()
    }
  },
)

onUnmounted(() => {
  document.body.style.overflow = ''
  document.removeEventListener('keydown', onKey)
})
</script>
