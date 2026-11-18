import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import AuthView from './AuthView.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'
import { doLogin } from '../utils/authStore.js'

vi.mock('../utils/authStore.js', () => ({
  doLogin: vi.fn(),
  doSignup: vi.fn(),
  auth: { user: null, ready: true },
  isAuthenticated: () => false,
}))

let app
let host

async function mount(mode = 'login') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', component: AuthView },
      { path: '/signup', component: AuthView },
    ],
  })
  router.push('/login')
  await router.isReady()
  host = document.createElement('div')
  document.body.appendChild(host)
  app = createApp(AuthView, { mode })
  app.use(router).use(i18n)
  app.mount(host)
}

async function fillAndSubmit(email, password) {
  host.querySelector('input[type="email"]').value = email
  host.querySelector('input[type="email"]').dispatchEvent(new Event('input'))
  host.querySelector('input[type="password"]').value = password
  host.querySelector('input[type="password"]').dispatchEvent(new Event('input'))
  host.querySelector('form').dispatchEvent(new Event('submit', { cancelable: true }))
  await new Promise((r) => setTimeout(r))
  await nextTick()
}

const errorText = () => host.querySelector('.auth-error')?.textContent.trim()

describe('AuthView', () => {
  beforeEach(() => {
    localStorage.clear()
    setLocale('en')
    vi.mocked(doLogin).mockReset()
  })
  afterEach(() => {
    app.unmount()
    host.remove()
    localStorage.clear()
    setLocale('en')
  })

  it('renders the English copy by default', async () => {
    await mount()
    expect(host.querySelector('h1').textContent).toBe('Welcome back')
    expect(host.querySelector('.auth-google').textContent).toContain('Continue with Google')
    expect(host.querySelector('.auth-submit').textContent.trim()).toBe('Log in')
  })

  it('follows the interface language', async () => {
    setLocale('tr')
    await mount('signup')
    await nextTick()
    expect(host.querySelector('h1').textContent).toBe('Hesabınızı oluşturun')
    expect(host.querySelector('.auth-google').textContent).toContain('Google ile devam et')
    expect(host.querySelector('.auth-switch a').textContent).toBe('Giriş yap')
  })

  it('shows a translated message for an API error code', async () => {
    setLocale('tr')
    await mount()
    doLogin.mockRejectedValue(
      Object.assign(new Error('x'), { status: 401, code: 'invalid_credentials' }),
    )
    await fillAndSubmit('a@b.co', 'longenough')
    expect(errorText()).toBe('E-posta adresi ya da parola yanlış.')
  })

  it('shows a translated message for a network failure', async () => {
    setLocale('tr')
    await mount()
    doLogin.mockRejectedValue(new TypeError('Failed to fetch'))
    await fillAndSubmit('a@b.co', 'longenough')
    expect(errorText()).toContain('Sunucuya ulaşılamıyor')
  })

  it('validates client-side in the interface language without calling the API', async () => {
    setLocale('tr')
    await mount()
    await fillAndSubmit('a@b.co', '')
    expect(errorText()).toBe('Parolanızı yazın.')
    await fillAndSubmit('a@b.co', 'short')
    expect(errorText()).toBe('En az 8 karakterli bir parola seçin.')
    expect(doLogin).not.toHaveBeenCalled()
  })

  it('links from log in to sign up', async () => {
    await mount()
    expect(host.querySelector('.auth-switch a').getAttribute('href')).toBe('/signup')
  })
})
