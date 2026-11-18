import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import AppTopbar from './AppTopbar.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'

vi.mock('../utils/authStore.js', () => ({
  auth: { user: { name: 'Demo User', email: 'demo@example.org' }, ready: true },
  doLogout: vi.fn(),
}))

let app
let host
let router

async function mount() {
  const Blank = { template: '<div />' }
  router = createRouter({
    history: createMemoryHistory(),
    routes: ['/', '/app', '/reports', '/settings'].map((path) => ({ path, component: Blank })),
  })
  await router.push('/reports')
  host = document.createElement('div')
  document.body.appendChild(host)
  app = createApp(AppTopbar, { context: 'M&E Reports' })
  app.use(router).use(i18n)
  app.mount(host)
  await nextTick()
}

const brand = () => host.querySelector('.brand')

describe('AppTopbar', () => {
  beforeEach(async () => {
    localStorage.clear()
    setLocale('en')
    await mount()
  })
  afterEach(() => {
    app.unmount()
    host.remove()
    setLocale('en')
    localStorage.clear()
  })

  it('links the brand to the landing page, named as the home page', () => {
    expect(brand().getAttribute('href')).toBe('/')
    expect(brand().getAttribute('aria-label')).toBe('Humanitaria home page')
  })

  it('names the home page in the interface language', async () => {
    setLocale('tr')
    await nextTick()
    expect(brand().getAttribute('aria-label')).toBe('Humanitaria ana sayfası')
  })

  it('reaches the landing page in one click, and keeps Chat in the app nav', async () => {
    brand().click()
    await new Promise((r) => setTimeout(r))
    expect(router.currentRoute.value.path).toBe('/')
    const chat = [...host.querySelectorAll('.app-nav-link')].map((a) => a.getAttribute('href'))
    expect(chat).toEqual(['/app', '/reports'])
  })
})
