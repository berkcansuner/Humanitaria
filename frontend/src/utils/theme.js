/**
 * Light/dark theme helpers. The theme is a UI preference stored in
 * localStorage (conversations live in the backend); the dark palette is
 * defined in style.css under `:root[data-theme="dark"]`.
 */

const STORAGE_KEY = 'theme'
const VALID = ['light', 'dark']

/**
 * Resolve the initial theme: a valid stored choice wins, otherwise fall back
 * to the OS `prefers-color-scheme`.
 * @returns {'light'|'dark'}
 */
export function getInitialTheme() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (VALID.includes(stored)) return stored
  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
  return prefersDark ? 'dark' : 'light'
}

/** Reflect the theme on <html> so the CSS variable overrides take effect. */
export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme
}

/** Persist the chosen theme and apply it immediately. */
export function setTheme(theme) {
  localStorage.setItem(STORAGE_KEY, theme)
  applyTheme(theme)
}
