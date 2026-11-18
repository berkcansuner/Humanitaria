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
const home = () => host.querySelector('.home-link')

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

  it('keeps the brand as the way back to chat', () => {
    expect(brand().getAttribute('href')).toBe('/app')
    expect(brand().getAttribute('title')).toBe('Humanitaria: back to chat')
    expect(brand().hasAttribute('aria-label')).toBe(false)
  })

  it('has a home page link of its own, named in the interface language', async () => {
    expect(home().getAttribute('href')).toBe('/')
    // The name is the link's own text (visually hidden on phones), so speech
    // input and screen readers get the word that is shown.
    expect(home().textContent.trim()).toBe('Home page')
    expect(home().getAttribute('title')).toBe('Home page')
    expect(home().hasAttribute('aria-label')).toBe(false)
    setLocale('tr')
    await nextTick()
    expect(home().textContent.trim()).toBe('Ana sayfa')
    expect(home().getAttribute('title')).toBe('Ana sayfa')
  })

  it('sits with the utilities, not among the Chat and Reports tabs', () => {
    expect(home().closest('.app-nav')).toBeNull()
    const order = [...host.querySelector('.app-topbar').children].map((el) => el.className)
    const at = (cls) => order.findIndex((c) => c.split(' ').includes(cls))
    expect(at('app-nav')).toBeLessThan(at('home-link'))
    expect(at('home-link')).toBeLessThan(at('lang-switcher'))
  })

  it('reaches the landing page in one click, and keeps Chat in the app nav', async () => {
    home().click()
    await new Promise((r) => setTimeout(r))
    expect(router.currentRoute.value.path).toBe('/')
    const chat = [...host.querySelectorAll('.app-nav-link')].map((a) => a.getAttribute('href'))
    expect(chat).toEqual(['/app', '/reports'])
  })
})

// Every signed-in screen draws this one top bar, so each gets the link.
describe('the app screens', () => {
  const views = import.meta.glob(
    '../views/{ChatView,ReportsView,SettingsView,AdminIngestionView}.vue',
    {
      query: '?raw',
      import: 'default',
      eager: true,
    },
  )

  it('all use AppTopbar', () => {
    expect(Object.keys(views)).toHaveLength(4)
    for (const [path, source] of Object.entries(views)) {
      expect(source, path).toMatch(/<AppTopbar[\s>]/)
    }
  })
})
