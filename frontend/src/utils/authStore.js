/**
 * Reactive auth state shared across the app. Kept deliberately small (a single
 * reactive object) — no Pinia, matching the project's lightweight state style.
 */
import { reactive } from 'vue'

import { me, login, signup, logout } from './authApi.js'

export const auth = reactive({
  user: null,   // { id, email, name } when signed in, else null
  ready: false, // true once the initial /auth/me probe has resolved
})

export function isAuthenticated() {
  return auth.user !== null
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
