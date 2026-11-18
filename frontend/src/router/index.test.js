import { describe, it, expect, beforeAll, beforeEach, afterAll, vi } from 'vitest'
import { router } from './index.js'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'

vi.mock('../utils/authStore.js', () => ({
  auth: { user: null, ready: true },
  refresh: vi.fn(),
  isAuthenticated: () => false,
  isAdmin: () => false,
}))

// jsdom has no scrolling; the router's scrollBehavior calls it on every navigation.
const realScrollTo = window.scrollTo
beforeAll(() => {
  window.scrollTo = () => {}
})
afterAll(() => {
  window.scrollTo = realScrollTo
  setLocale('en')
  localStorage.clear()
})

// A shared ?lang= link is an explicit choice: applied, then dropped from the URL.
describe('?lang= links', () => {
  beforeEach(async () => {
    setLocale('en')
    await router.push('/')
    localStorage.clear()
  })

  it('applies the language and drops only lang from the query', async () => {
    await router.push('/privacy?lang=tr&ref=mail')
    expect(i18n.global.locale.value).toBe('tr')
    expect(localStorage.getItem('lang')).toBe('tr')
    expect(router.currentRoute.value.path).toBe('/privacy')
    expect(router.currentRoute.value.query).toEqual({ ref: 'mail' })
  })

  it('normalises the case of the code', async () => {
    await router.push('/privacy?lang=TR')
    expect(i18n.global.locale.value).toBe('tr')
    expect(router.currentRoute.value.query).toEqual({})
  })

  it('ignores a language the interface does not have', async () => {
    await router.push('/privacy?lang=de')
    expect(i18n.global.locale.value).toBe('en')
    expect(localStorage.getItem('lang')).toBeNull()
  })
})
