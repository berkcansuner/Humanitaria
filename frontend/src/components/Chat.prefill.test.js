import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createApp, h, KeepAlive, nextTick } from 'vue'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'
import Chat from './Chat.vue'
import { ASK_STORAGE_KEY, prefillFor } from '../utils/askQuestion.js'
import { i18n } from '../i18n/index.js'

async function mountChat(url) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/app', component: Chat }],
  })
  router.push(url)
  await router.isReady()
  const host = document.createElement('div')
  document.body.appendChild(host)
  const app = createApp(Chat, { conversationId: null })
  app.use(router).use(i18n)
  app.mount(host)
  await nextTick()
  await nextTick()
  return { router, host, app, textarea: () => host.querySelector('textarea') }
}

describe('Chat composer prefill from the landing ask', () => {
  beforeEach(() => {
    sessionStorage.clear()
    document.body.innerHTML = ''
  })

  it('fills the composer from ?q and never sends', async () => {
    const { textarea } = await mountChat('/app?q=Sudan%20IDPs')
    expect(textarea().value).toBe('Sudan IDPs')
  })

  it('strips q from the URL but keeps other query keys', async () => {
    const { router } = await mountChat('/app?q=Sudan&conv=7')
    await vi.waitFor(() => expect(router.currentRoute.value.query.q).toBeUndefined())
    expect(router.currentRoute.value.query).toEqual({ conv: '7' })
  })

  it('falls back to the stashed question when q is absent, then clears it', async () => {
    sessionStorage.setItem(ASK_STORAGE_KEY, 'Haiti cholera')
    const { textarea } = await mountChat('/app')
    expect(textarea().value).toBe('Haiti cholera')
    expect(sessionStorage.getItem(ASK_STORAGE_KEY)).toBeNull()
  })

  it('clears the stash when q was used and prefers q', async () => {
    sessionStorage.setItem(ASK_STORAGE_KEY, 'stale')
    const { textarea } = await mountChat('/app?q=fresh')
    expect(textarea().value).toBe('fresh')
    expect(sessionStorage.getItem(ASK_STORAGE_KEY)).toBeNull()
  })
})

// The app keeps the chat screen alive across screens (App.vue), so a landing ask
// can reach a chat that is already mounted.
describe('Chat kept alive across screens', () => {
  beforeEach(() => {
    sessionStorage.clear()
    document.body.innerHTML = ''
  })

  async function mountKept() {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/app', component: Chat },
        { path: '/reports', component: { name: 'Reports', render: () => h('p') } },
      ],
    })
    router.push('/app')
    await router.isReady()
    const Shell = {
      render: () =>
        h(RouterView, null, {
          default: ({ Component }) =>
            h(KeepAlive, { include: ['Chat'] }, Component ? [h(Component)] : []),
        }),
    }
    const host = document.createElement('div')
    document.body.appendChild(host)
    const app = createApp(Shell).use(router).use(i18n)
    app.mount(host)
    await nextTick()
    return { router, host, app }
  }

  it('fills the composer from ?q when the chat comes back from the cache', async () => {
    const { router, host } = await mountKept()
    await router.push('/reports')
    await router.push('/app?q=Yemen%20cholera')
    await nextTick()
    expect(host.querySelector('textarea').value).toBe('Yemen cholera')
  })

  it('stops a streaming answer when the chat is unmounted', async () => {
    let signal
    vi.stubGlobal(
      'fetch',
      vi.fn((url, init) => {
        signal = init.signal
        return new Promise(() => {})
      }),
    )
    const { host, app } = await mountKept()
    const textarea = host.querySelector('textarea')
    textarea.value = 'Sudan IDPs'
    textarea.dispatchEvent(new Event('input'))
    textarea.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    await vi.waitFor(() => expect(signal).toBeDefined())
    app.unmount()
    expect(signal.aborted).toBe(true)
    vi.unstubAllGlobals()
  })
})

describe('prefillFor', () => {
  it('never replaces text already in the composer', () => {
    expect(prefillFor('my draft', 'Sudan', 'stashed')).toBe('')
  })
  it('prefers q over the stash and trims it', () => {
    expect(prefillFor('', ' Sudan ', 'stashed')).toBe('Sudan')
  })
  it('uses the stash when q is absent', () => {
    expect(prefillFor('', undefined, 'stashed')).toBe('stashed')
  })
})
