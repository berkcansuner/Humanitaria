import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import SettingsView from './SettingsView.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'
import { changePassword, deleteAccount } from '../utils/authApi.js'

vi.mock('../utils/authStore.js', () => ({
  auth: {
    user: { id: 'u1', email: 'a@example.org', name: 'Ada', has_password: true, is_admin: false },
    ready: true,
  },
  doLogout: vi.fn(),
}))
vi.mock('../utils/authApi.js', () => ({
  updateProfile: vi.fn(),
  changePassword: vi.fn(),
  deleteAccount: vi.fn(),
  updateLanguage: vi.fn(),
}))

let app
let host

async function mount() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: SettingsView }],
  })
  router.push('/')
  await router.isReady()
  host = document.createElement('div')
  document.body.appendChild(host)
  app = createApp(SettingsView)
  app.use(router).use(i18n)
  app.mount(host)
}

function type(input, value) {
  input.value = value
  input.dispatchEvent(new Event('input'))
}

async function submitPasswordForm(current, next, repeat) {
  const [cur, nw, rep] = host.querySelectorAll('input[type="password"]')
  type(cur, current)
  type(nw, next)
  type(rep, repeat)
  host.querySelector('form[novalidate]').dispatchEvent(new Event('submit', { cancelable: true }))
  await new Promise((r) => setTimeout(r))
  await nextTick()
}

const pwError = () => host.querySelector('#pw-error')?.textContent.trim()

describe('SettingsView', () => {
  beforeEach(() => {
    localStorage.clear()
    setLocale('en')
    vi.mocked(changePassword).mockReset()
    vi.mocked(deleteAccount).mockReset()
  })
  afterEach(() => {
    app.unmount()
    host.remove()
    localStorage.clear()
    setLocale('en')
  })

  it('uses the same section names as the privacy page path', async () => {
    await mount()
    const headings = [...host.querySelectorAll('h2')].map((h) => h.textContent)
    expect(headings).toContain('Delete account')
    expect(i18n.global.t('privacy.s4.path')).toBe('Settings → Delete account')
    setLocale('tr')
    await nextTick()
    expect([...host.querySelectorAll('h2')].map((h) => h.textContent)).toContain('Hesabı sil')
    expect(i18n.global.t('privacy.s4.path')).toBe('Ayarlar → Hesabı sil')
  })

  it('checks the password form in the interface language, not the browser', async () => {
    setLocale('tr')
    await mount()
    await submitPasswordForm('', '', '')
    expect(pwError()).toBe('Parolanızı yazın.')
    expect(changePassword).not.toHaveBeenCalled()
    const [cur] = host.querySelectorAll('input[type="password"]')
    expect(cur.getAttribute('aria-invalid')).toBe('true')
    expect(cur.getAttribute('aria-describedby')).toBe('pw-error')
    expect(document.activeElement).toBe(cur)
  })

  it('flags mismatching new passwords', async () => {
    await mount()
    await submitPasswordForm('old-password', 'new-password-1', 'new-password-2')
    expect(pwError()).toBe('New passwords do not match.')
  })

  it('keeps a request error as an error so it follows a language switch', async () => {
    await mount()
    changePassword.mockRejectedValue(
      Object.assign(new Error('x'), { status: 403, code: 'wrong_password' }),
    )
    await submitPasswordForm('wrong-password', 'new-password-1', 'new-password-1')
    expect(pwError()).toBe('That password is incorrect.')
    setLocale('tr')
    await nextTick()
    expect(pwError()).toBe('Parola yanlış.')
  })

  it('names the failed action when the error has no code', async () => {
    await mount()
    changePassword.mockRejectedValue(Object.assign(new Error('x'), { status: 500 }))
    await submitPasswordForm('old-password', 'new-password-1', 'new-password-1')
    expect(pwError()).toBe('Could not change the password. Please try again.')
    setLocale('tr')
    await nextTick()
    expect(pwError()).toBe('Parola değiştirilemedi. Lütfen yeniden deneyin.')
  })

  it('marks the delete input invalid only for errors about that field', async () => {
    await mount()
    host.querySelector('.danger-quiet-btn').click()
    await nextTick()
    const input = host.querySelector('.modal input')
    type(input, 'secret-password')
    deleteAccount.mockRejectedValue(Object.assign(new Error('x'), { status: 500 }))
    host.querySelector('.modal form').dispatchEvent(new Event('submit', { cancelable: true }))
    await new Promise((r) => setTimeout(r))
    await nextTick()
    expect(host.querySelector('#delete-error')).not.toBeNull()
    expect(input.getAttribute('aria-invalid')).toBeNull()
    deleteAccount.mockRejectedValue(
      Object.assign(new Error('x'), { status: 403, code: 'wrong_password' }),
    )
    host.querySelector('.modal form').dispatchEvent(new Event('submit', { cancelable: true }))
    await new Promise((r) => setTimeout(r))
    await nextTick()
    expect(input.getAttribute('aria-invalid')).toBe('true')
    expect(input.getAttribute('aria-describedby')).toBe('delete-error')
  })
})
