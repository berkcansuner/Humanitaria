import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest'
import { router } from './index.js'

// A signed-in visitor: the landing page stays reachable, the auth pages do not.
vi.mock('../utils/authStore.js', () => ({
  auth: { user: { id: 'u1', name: 'Demo User' }, ready: true },
  refresh: vi.fn(),
  isAuthenticated: () => true,
  isAdmin: () => false,
}))

// jsdom has no scrolling; the router's scrollBehavior calls it on every navigation.
const realScrollTo = window.scrollTo
beforeAll(() => {
  window.scrollTo = () => {}
})
afterAll(() => {
  window.scrollTo = realScrollTo
})

describe('router, signed in', () => {
  it('shows the landing page at the site root (no redirect into the app)', async () => {
    await router.push('/app')
    await router.push('/')
    expect(router.currentRoute.value.fullPath).toBe('/')
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('keeps landing sections reachable by their anchors', async () => {
    await router.push({ path: '/', hash: '#coverage' })
    expect(router.currentRoute.value.fullPath).toBe('/#coverage')
  })

  it('still sends the auth pages into the app', async () => {
    await router.push('/')
    await router.push('/login')
    expect(router.currentRoute.value.path).toBe('/app')
    await router.push('/signup')
    expect(router.currentRoute.value.path).toBe('/app')
  })

  it('lets a landing question through to the app', async () => {
    await router.push('/app?q=Who%20has%20returned%20to%20Syria%3F')
    expect(router.currentRoute.value.path).toBe('/app')
    expect(router.currentRoute.value.query.q).toBe('Who has returned to Syria?')
  })
})
