/**
 * Light/dark theme helpers. The theme is a UI preference stored in
 * localStorage (conversations live in the backend); the dark palette is
 * defined in style.css under `:root[data-theme="dark"]`.
 */

const STORAGE_KEY = 'theme'
const VALID = ['light', 'dark']

/**
 * Resolve the initial theme: a valid stored choice wins, otherwise light.
 * (The OS prefers-color-scheme fallback was removed on purpose — the product
 * default is light; users opt into dark from the settings page.)
 * @returns {'light'|'dark'}
 */
export function getInitialTheme() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (VALID.includes(stored)) return stored
  return 'light'
}

/** Reflect the theme on <html> so the CSS variable overrides take effect. */
export function applyTheme(theme) {
  const root = document.documentElement
  root.dataset.theme = theme
  // Native UI (scrollbars, caret, form widgets) follows this; without it dark
  // mode leaves light-mode scrollbars and a hard-to-see caret.
  root.style.colorScheme = theme
  // Keep the mobile browser chrome in sync with the page background.
  const bg = getComputedStyle(root).getPropertyValue('--color-bg').trim()
  if (bg) {
    let meta = document.querySelector('meta[name="theme-color"]')
    if (!meta) {
      meta = document.createElement('meta')
      meta.setAttribute('name', 'theme-color')
      document.head.appendChild(meta)
    }
    meta.setAttribute('content', bg)
  }
}

/** Persist the chosen theme and apply it immediately. */
export function setTheme(theme) {
  localStorage.setItem(STORAGE_KEY, theme)
  applyTheme(theme)
}
