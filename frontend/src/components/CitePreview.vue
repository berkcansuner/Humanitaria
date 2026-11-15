<template>
  <!-- A small card naming the source behind a [n] chip, so a reader can check a
       claim without leaving their place. Reads the data from the Sources ledger
       already on the page (same message, or the report viewer). Hover and focus
       open it; the pointer may move onto it; it follows the chip on scroll; Escape,
       blur, or the chip leaving the window close it. -->
  <Teleport to="body">
    <div
      v-if="card"
      class="cite-preview"
      :class="{ below: card.below }"
      role="tooltip"
      :style="{ top: card.top + 'px', left: card.left + 'px' }"
      @mouseenter="cancelHide"
      @mouseleave="scheduleHide"
    >
      <span class="cp-title">{{ card.title }}</span>
      <span v-if="card.meta" class="cp-meta">{{ card.meta }}</span>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  // The element whose .cite chips get previews (chat message list, report viewer).
  root: { type: Object, default: null },
})

const WIDTH = 300
const card = ref(null)
let current = null // the chip the card belongs to
let showTimer = null
let hideTimer = null
let frame = 0

function infoFor(cite) {
  const id = cite.getAttribute('data-cite')
  const scope = cite.closest('.message') || props.root
  const row = scope?.querySelector(`.source-item[data-srcid="${id}"]`)
  if (!row) return null // still streaming, or a source that is not shown
  const title = row.querySelector('.source-title-text')?.textContent.trim()
  if (!title) return null
  const publisher = row.querySelector('.source-meta')?.textContent.trim()
  const date = row.querySelector('time')?.textContent.trim()
  return { title, meta: [publisher, date].filter(Boolean).join(' · ') }
}

function show(cite) {
  const info = infoFor(cite)
  if (!info) return
  current = cite
  const r = cite.getBoundingClientRect()
  if (r.bottom < 0 || r.top > window.innerHeight) {
    hide()
    return
  }
  const left = Math.min(
    Math.max(8, r.left + r.width / 2 - WIDTH / 2),
    window.innerWidth - WIDTH - 8,
  )
  // Above the chip, unless that would run off the top of the window.
  const below = r.top < 96
  card.value = { ...info, left, below, top: below ? r.bottom + 8 : r.top - 8 }
}

function hide() {
  clearTimeout(showTimer)
  clearTimeout(hideTimer)
  current = null
  card.value = null
}

// Follow the chip while the page scrolls (focusing a chip can itself scroll it
// into view); close only once it has left the window.
function onScroll() {
  if (!current || !card.value) return
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(() => current && show(current))
}

function scheduleHide() {
  clearTimeout(showTimer)
  clearTimeout(hideTimer)
  hideTimer = setTimeout(hide, 150)
}

function cancelHide() {
  clearTimeout(hideTimer)
}

function citeFrom(e) {
  return e.target && e.target.closest ? e.target.closest('.cite') : null
}

function onOver(e) {
  const cite = citeFrom(e)
  if (!cite) return
  clearTimeout(hideTimer)
  clearTimeout(showTimer)
  showTimer = setTimeout(() => show(cite), 150)
}

function onOut(e) {
  if (citeFrom(e)) scheduleHide()
}

function onFocusIn(e) {
  const cite = citeFrom(e)
  if (!cite) return
  // Tabbing between chips fires focusout on the old one first; cancel its
  // pending hide so it does not close the card just opened for the new one.
  clearTimeout(hideTimer)
  clearTimeout(showTimer)
  show(cite)
}

function onKey(e) {
  if (e.key === 'Escape') hide()
}

const listeners = [
  ['mouseover', onOver],
  ['mouseout', onOut],
  ['focusin', onFocusIn],
  ['focusout', onOut],
]

watch(
  () => props.root,
  (el, old) => {
    if (old) listeners.forEach(([type, fn]) => old.removeEventListener(type, fn))
    if (el) listeners.forEach(([type, fn]) => el.addEventListener(type, fn))
  },
  { immediate: true },
)

window.addEventListener('scroll', onScroll, true)
document.addEventListener('keydown', onKey)

onBeforeUnmount(() => {
  hide()
  if (props.root) listeners.forEach(([type, fn]) => props.root.removeEventListener(type, fn))
  cancelAnimationFrame(frame)
  window.removeEventListener('scroll', onScroll, true)
  document.removeEventListener('keydown', onKey)
})
</script>

<style scoped>
.cite-preview {
  position: fixed;
  z-index: 70;
  width: 300px;
  max-width: calc(100vw - 16px);
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 8px 10px;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  transform: translateY(-100%);
}

.cite-preview.below {
  transform: none;
}

.cp-title {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--color-text);
}

.cp-meta {
  font-family: var(--font-mono);
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}
</style>
