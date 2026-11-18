export const SUPPORTED = ['en', 'tr']
const DEFAULT_LOCALE = 'en'
const STORAGE_KEY = 'lang'

const listeners = new Set()
// An explicit choice storage refused to keep: it still counts for this page view,
// so signing in does not replace it with the account's language.
let unstoredChoice = false

export function normalizeLocale(value) {
  if (typeof value !== 'string') return null
  const v = value.trim().toLowerCase()
  return SUPPORTED.includes(v) ? v : null
}

// Storage can throw (private mode, blocked site data); callers never see it.
function readStored() {
  try {
    return normalizeLocale(localStorage.getItem(STORAGE_KEY))
  } catch {
    return null
  }
}

export function hasExplicitChoice() {
  return unstoredChoice || readStored() !== null
}

export function initialLocale() {
  return readStored() ?? DEFAULT_LOCALE
}

function apply(next, info) {
  document.documentElement.lang = next
  for (const cb of listeners) cb(next, info)
}

export function setLocale(locale, { explicit = true } = {}) {
  const next = normalizeLocale(locale)
  if (!next) return
  if (explicit) {
    try {
      localStorage.setItem(STORAGE_KEY, next)
      unstoredChoice = false
    } catch {
      // Not persisted; the choice still applies for this page view.
      unstoredChoice = true
    }
  }
  apply(next, { explicit })
}

// Another tab stored an explicit choice: show it here too. It is already stored
// and that tab writes it to the account, so listeners are told it came from
// another tab and this tab neither stores nor saves it again.
window.addEventListener('storage', (e) => {
  if (e.key !== STORAGE_KEY) return
  const next = normalizeLocale(e.newValue)
  if (next && next !== document.documentElement.lang) {
    apply(next, { explicit: true, fromOtherTab: true })
  }
})

export function onLocaleChange(cb) {
  listeners.add(cb)
  return () => listeners.delete(cb)
}
