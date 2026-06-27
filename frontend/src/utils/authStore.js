/**
 * Reactive auth state shared across the app. Kept deliberately small (a single
 * reactive object) — no Pinia, matching the project's lightweight state style.
 */
import { reactive } from 'vue'

import { me, login, signup, logout } from './authApi.js'

export const auth = reactive({
  user: null,   // { id, email, name, is_admin } when signed in, else null
  ready: false, // true once the initial /auth/me probe has resolved
})

export function isAuthenticated() {
  return auth.user !== null
}

export function isAdmin() {
  return auth.user?.is_admin === true
}

/** Probe the session once on startup / before a guarded navigation. */
export async function refresh() {
  try {
    auth.user = await me()
  } catch {
    auth.user = null
  }
  auth.ready = true
  return auth.user
}

export async function doLogin(email, password) {
  auth.user = await login(email, password)
  return auth.user
}

export async function doSignup(email, password, name) {
  auth.user = await signup(email, password, name)
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
