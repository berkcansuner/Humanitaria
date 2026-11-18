import { describe, it, expect, beforeAll, afterAll, beforeEach, afterEach, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import LandingView from './LandingView.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'
import { auth } from '../utils/authStore.js'

vi.mock('../utils/authStore.js', async () => {
  const { reactive } = await import('vue')
  const auth = reactive({ user: null, ready: true })
  return { auth, isAuthenticated: () => auth.user !== null, doLogout: vi.fn() }
})

// jsdom lacks the browser APIs the hero's motion and map use; reduced motion keeps
// every animation off, and the map draws on a stand-in canvas.
const realGetContext = HTMLCanvasElement.prototype.getContext
class NoObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
beforeAll(() => {
  vi.stubGlobal('matchMedia', (query) => ({
    matches: query.includes('reduce'),
    media: query,
    addEventListener() {},
    removeEventListener() {},
    addListener() {},
    removeListener() {},
  }))
  vi.stubGlobal('IntersectionObserver', NoObserver)
  vi.stubGlobal('ResizeObserver', NoObserver)
  // A 2D context that accepts any drawing call (and any call on what it returns).
  const ctx = new Proxy(function () {}, {
    get: (target, key) => (key in target ? target[key] : ctx),
    set: (target, key, value) => ((target[key] = value), true),
    apply: () => ctx,
  })
  HTMLCanvasElement.prototype.getContext = () => ctx
})
afterAll(() => {
  vi.unstubAllGlobals()
  HTMLCanvasElement.prototype.getContext = realGetContext
})

let app
let host
let router

async function mount() {
  const Blank = { template: '<div />' }
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: LandingView },
      ...['/app', '/login', '/signup', '/privacy'].map((path) => ({ path, component: Blank })),
    ],
  })
  await router.push('/')
  host = document.createElement('div')
  document.body.appendChild(host)
  app = createApp({ template: '<router-view />' })
  app.use(router).use(i18n)
  app.mount(host)
  await nextTick()
}

const links = (sel) =>
  [...host.querySelectorAll(sel)].map((a) => [a.textContent.trim(), a.getAttribute('href')])

describe('LandingView calls to action', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setLocale('en')
  })
  afterEach(() => {
    app.unmount()
    host.remove()
    auth.user = null
    setLocale('en')
  })

  it('asks a visitor to start free or log in', async () => {
    await mount()
    expect(links('.hero-cta > a')[0]).toEqual(['Start free', '/signup'])
    expect(links('.cta-btns > a')).toEqual([
      ['Start free', '/signup'],
      ['Log in', '/login'],
    ])
  })

  it('opens the app for a signed-in visitor instead', async () => {
    auth.user = { id: 'u1', name: 'Demo User' }
    await mount()
    expect(links('.hero-cta > a')).toEqual([
      ['Open app', '/app'],
      ['See how it works', '/#workflows'],
    ])
    expect(links('.cta-btns > a')).toEqual([['Open app', '/app']])
  })

  it('sends a signed-in question straight to the app', async () => {
    auth.user = { id: 'u1', name: 'Demo User' }
    await mount()
    const input = host.querySelector('#ask-input')
    input.value = 'Who has returned to Syria?'
    input.dispatchEvent(new Event('input'))
    host.querySelector('form.ask').dispatchEvent(new Event('submit'))
    await new Promise((r) => setTimeout(r))
    expect(router.currentRoute.value.path).toBe('/app')
    expect(router.currentRoute.value.query.q).toBe('Who has returned to Syria?')
  })
})
