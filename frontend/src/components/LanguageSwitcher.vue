<template>
  <div ref="rootEl" class="lang-switcher" :class="`is-${variant}`">
    <button
      ref="buttonEl"
      type="button"
      class="lang-btn"
      aria-haspopup="listbox"
      :aria-expanded="open ? 'true' : 'false'"
      :aria-controls="open ? listId : undefined"
      :aria-label="t('lang.buttonLabel', { name: current.name })"
      @click="toggle"
      @keydown.down.prevent="openList"
    >
      <Globe :size="16" aria-hidden="true" />
      <span class="lang-code" aria-hidden="true">{{ current.code.toUpperCase() }}</span>
    </button>
    <ul
      v-if="open"
      :id="listId"
      ref="listEl"
      class="lang-list"
      role="listbox"
      tabindex="-1"
      :aria-label="t('lang.listLabel')"
      :aria-activedescendant="optionId(active)"
      @keydown="onListKey"
    >
      <li
        v-for="(l, i) in LANGUAGES"
        :id="optionId(i)"
        :key="l.code"
        class="lang-option"
        :class="{ 'is-active': i === active }"
        role="option"
        :lang="l.code"
        :aria-selected="l.code === locale ? 'true' : 'false'"
        @click="choose(l.code)"
        @mousemove="active = i"
      >
        <span>{{ l.name }}</span>
        <Check v-if="l.code === locale" :size="15" aria-hidden="true" />
      </li>
    </ul>
    <span class="lang-live" role="status" aria-live="polite">{{ announcement }}</span>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount, useId } from 'vue'
import { Globe, Check } from 'lucide-vue-next'
import { t, useLocale } from '../i18n/index.js'

defineProps({
  // Surface the switcher sits on: the marketing nav or the signed-in top bar.
  variant: { type: String, default: 'app', validator: (v) => ['marketing', 'app'].includes(v) },
})

// Endonyms: each language is always named in itself, never translated.
const LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'tr', name: 'Türkçe' },
]

const { locale, setLocale } = useLocale()
const uid = useId()
const listId = `lang-list-${uid}`
const optionId = (i) => `lang-opt-${uid}-${i}`

const open = ref(false)
const active = ref(0)
const announcement = ref('')
const rootEl = ref(null)
const buttonEl = ref(null)
const listEl = ref(null)

const current = computed(() => LANGUAGES.find((l) => l.code === locale.value) ?? LANGUAGES[0])

async function openList() {
  if (open.value) return
  active.value = Math.max(
    0,
    LANGUAGES.findIndex((l) => l.code === locale.value),
  )
  open.value = true
  await nextTick()
  listEl.value?.focus()
}

function toggle() {
  if (open.value) closeList()
  else openList()
}

function closeList({ refocus = true } = {}) {
  open.value = false
  if (refocus) buttonEl.value?.focus()
}

function choose(code) {
  const changed = code !== locale.value
  setLocale(code)
  closeList()
  // The locale ref flips synchronously, so this reads in the new language.
  if (changed) announcement.value = t('lang.changed', { name: current.value.name })
}

function onListKey(e) {
  const last = LANGUAGES.length - 1
  switch (e.key) {
    case 'ArrowDown':
      active.value = Math.min(active.value + 1, last)
      break
    case 'ArrowUp':
      active.value = Math.max(active.value - 1, 0)
      break
    case 'Home':
      active.value = 0
      break
    case 'End':
      active.value = last
      break
    case 'Enter':
    case ' ':
      choose(LANGUAGES[active.value].code)
      break
    case 'Escape':
      closeList()
      break
    case 'Tab':
      // Let focus move on naturally; just dismiss the popup.
      closeList({ refocus: false })
      return
    default:
      return
  }
  e.preventDefault()
}

function onDocClick(e) {
  if (open.value && rootEl.value && !rootEl.value.contains(e.target)) closeList({ refocus: false })
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<style scoped>
.lang-switcher {
  position: relative;
  flex-shrink: 0;
}

.lang-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--color-text-secondary);
  font-family: var(--font-body);
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition:
    background-color 0.15s,
    color 0.15s,
    border-color 0.15s;
}

.lang-btn:hover,
.lang-btn[aria-expanded='true'] {
  color: var(--color-text);
  background-color: var(--color-surface-container-low);
}

.lang-btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* Focus stays on the list (aria-activedescendant), so the ring goes on the
   active option rather than around the whole popup. */
.lang-list:focus {
  outline: none;
}
.lang-list:focus-visible .lang-option.is-active {
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}

/* Marketing: a full 44px pill, level with the nav's other buttons. */
.is-marketing .lang-btn {
  min-width: 44px;
  min-height: 44px;
  padding: 0 14px;
  border-radius: 999px;
  font-size: 14px;
}

@media (max-width: 560px) {
  .is-marketing .lang-btn {
    padding: 0 10px;
  }
}

/* App: as compact as the 28px top-bar controls; an invisible pad brings the
   hit area to 44px. */
.is-app .lang-btn {
  height: 28px;
  padding: 0 8px;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}
.is-app .lang-btn:hover,
.is-app .lang-btn[aria-expanded='true'] {
  background-color: var(--color-surface-container);
}
.is-app .lang-btn::after {
  content: '';
  position: absolute;
  inset: -8px -4px;
}

.lang-list {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  min-width: 168px;
  margin: 0;
  padding: var(--space-1);
  list-style: none;
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 60;
}

.lang-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  min-height: 44px;
  padding: 0 var(--space-3);
  color: var(--color-text-secondary);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  border-radius: var(--radius-md);
  cursor: pointer;
}

.lang-option.is-active {
  background-color: var(--color-surface-container-low);
  color: var(--color-text);
}

.lang-option[aria-selected='true'] {
  color: var(--color-accent);
  font-weight: 600;
}

.lang-live {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .lang-btn {
    transition: none;
  }
}
</style>
