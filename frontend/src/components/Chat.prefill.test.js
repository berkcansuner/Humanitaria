import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
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
