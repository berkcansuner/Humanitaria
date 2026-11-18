/**
 * Reactive auth state shared across the app. Kept deliberately small (a single
 * reactive object) — no Pinia, matching the project's lightweight state style.
 */
import { reactive } from 'vue'

import { me, login, signup, logout, updateLanguage } from './authApi.js'
import { hasExplicitChoice, onLocaleChange, setLocale } from '../i18n/locale.js'

export const auth = reactive({
  user: null, // { id, email, name, is_admin, auth_provider, has_password, ui_language } when signed in, else null
  ready: false, // true once the initial /auth/me probe has resolved
})

export function isAuthenticated() {
  return auth.user !== null
}

export function isAdmin() {
  return auth.user?.is_admin === true
}

function saveLanguage(lang) {
  updateLanguage(lang).catch((err) => console.warn('Could not save the interface language', err))
}

// Reconcile the device language with the account's. An explicit device choice
// wins and is written to the account; otherwise the account language applies
// (not stored on the device, so it never counts as an explicit choice).
function syncLanguage(user) {
  if (!user) return
  if (hasExplicitChoice()) {
    const current = document.documentElement.lang
    if (current !== user.ui_language) saveLanguage(current)
  } else if (user.ui_language) {
    setLocale(user.ui_language, { explicit: false })
  }
}

// A language picked while signed in goes to the account; applying the account's
// own value is non-explicit and is not echoed back. Subscribed once at load.
onLocaleChange((lang, { explicit }) => {
  if (explicit && auth.user) saveLanguage(lang)
})

/** Probe the session once on startup / before a guarded navigation. */
export async function refresh() {
  try {
    auth.user = await me()
  } catch {
    auth.user = null
  }
  auth.ready = true
  syncLanguage(auth.user)
  return auth.user
}

export async function doLogin(email, password) {
  auth.user = await login(email, password)
  syncLanguage(auth.user)
  return auth.user
}

export async function doSignup(email, password, name) {
  auth.user = await signup(email, password, name)
  syncLanguage(auth.user)
  return auth.user
}

export async function doLogout() {
  try {
    await logout()
  } finally {
    auth.user = null
  }
}

/**
 * Called when an API call returns 401 mid-session (the session cookie expired or
 * was invalidated server-side). Clears local auth state and bounces the user to
 * the login page — the router guard alone can't catch this because no navigation
 * happens while the user sits on /app. The router is imported lazily to avoid a
 * static import cycle (router/index.js imports this module).
 */
export async function handleSessionExpired() {
  auth.user = null
  const { router } = await import('../router/index.js')
  if (router.currentRoute.value.name !== 'login') {
    router.push({ path: '/login', query: { redirect: '/app' } })
  }
}
