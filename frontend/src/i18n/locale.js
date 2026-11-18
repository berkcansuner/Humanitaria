export const SUPPORTED = ['en', 'tr']
const DEFAULT_LOCALE = 'en'
const STORAGE_KEY = 'lang'

const listeners = new Set()

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
  return readStored() !== null
}

export function initialLocale() {
  return readStored() ?? DEFAULT_LOCALE
}

export function setLocale(locale, { explicit = true } = {}) {
  const next = normalizeLocale(locale)
  if (!next) return
  document.documentElement.lang = next
  if (explicit) {
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Not persisted; the choice still applies for this page view.
    }
  }
  for (const cb of listeners) cb(next)
}

export function onLocaleChange(cb) {
  listeners.add(cb)
  return () => listeners.delete(cb)
}
