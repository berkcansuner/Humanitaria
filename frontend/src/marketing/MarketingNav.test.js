import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import MarketingNav from './MarketingNav.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'
import { auth } from '../utils/authStore.js'

vi.mock('../utils/authStore.js', async () => {
  const { reactive } = await import('vue')
  const auth = reactive({ user: null, ready: true })
  return {
    auth,
    isAuthenticated: () => auth.user !== null,
    doLogout: vi.fn(async () => {
      auth.user = null
    }),
  }
})

let app
let host

async function mount() {
  const Blank = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: ['/', '/app', '/login', '/signup'].map((path) => ({ path, component: Blank })),
  })
  await router.push('/')
  host = document.createElement('div')
  document.body.appendChild(host)
  app = createApp(MarketingNav)
  app.use(router).use(i18n)
  app.mount(host)
  await nextTick()
}

// The account actions after the language selector: [text, href or 'button', solid?].
const actions = () =>
  [...host.querySelectorAll('.nav-right > a, .nav-right > button.btn')].map((el) => [
    el.textContent.trim(),
    el.getAttribute('href') || 'button',
    el.classList.contains('btn-solid'),
  ])

describe('MarketingNav', () => {
  beforeEach(() => {
    localStorage.clear()
    setLocale('en')
  })
  afterEach(() => {
    app.unmount()
    host.remove()
    auth.user = null
    setLocale('en')
  })

  it('offers log in and the solid Start free to a visitor', async () => {
    await mount()
    expect(actions()).toEqual([
      ['Log in', '/login', false],
      ['Start free', '/signup', true],
    ])
  })

  it('makes Open app the solid action for a signed-in visitor, with Log out beside it', async () => {
    auth.user = { id: 'u1', name: 'Demo User' }
    await mount()
    // Log out comes first as the quiet text button; on phones it hides like Log in.
    expect(actions()).toEqual([
      ['Log out', 'button', false],
      ['Open app', '/app', true],
    ])
    setLocale('tr')
    await nextTick()
    expect(actions().map((a) => a[0])).toEqual(['Çıkış yap', 'Uygulamayı aç'])
  })
})
