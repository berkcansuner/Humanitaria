import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import ChatView from './ChatView.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'
import { listConversations, getMessages } from '../utils/api.js'
import en from '../locales/en.json'
import tr from '../locales/tr.json'

vi.mock('../utils/api.js', () => ({
  listConversations: vi.fn(),
  renameConversation: vi.fn(),
  deleteConversation: vi.fn(),
  getMessages: vi.fn().mockResolvedValue([]),
  truncateConversation: vi.fn(),
}))
vi.mock('../utils/authStore.js', () => ({
  auth: { user: { name: 'Demo User', email: 'demo@example.org' }, ready: true },
  doLogout: vi.fn(),
  handleSessionExpired: vi.fn(),
}))

let app
let host
let router

async function mount(path = '/app') {
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/app', component: ChatView },
      { path: '/:rest(.*)*', component: { render: () => null } },
    ],
  })
  router.push(path)
  await router.isReady()
  host = document.createElement('div')
  document.body.appendChild(host)
  app = createApp(ChatView)
  app.use(router).use(i18n)
  app.mount(host)
  await flush()
}

const flush = async () => {
  for (let i = 0; i < 3; i++) {
    await new Promise((r) => setTimeout(r))
    await nextTick()
  }
}
const text = (sel) => host.querySelector(sel)?.textContent.trim()

describe('ChatView in two languages', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setLocale('en')
    vi.mocked(listConversations).mockReset()
  })
  afterEach(() => {
    app.unmount()
    host.remove()
    localStorage.clear()
    setLocale('en')
  })

  it('shows a failed list load in the current language, and switches with it', async () => {
    vi.mocked(listConversations).mockRejectedValue(new Error('down'))
    await mount()
    expect(text('.action-error span')).toBe(en.chat.actionErrors.load)
    setLocale('tr')
    await flush()
    expect(text('.action-error span')).toBe(tr.chat.actionErrors.load)
  })

  it('keeps the undo toast in step with a language switch', async () => {
    vi.mocked(listConversations).mockResolvedValue([
      { id: 'a', title: 'Sudan access', updated_at: new Date().toISOString() },
    ])
    await mount()
    host.querySelectorAll('.conv-action')[1].click()
    await flush()
    expect(text('.toast-text')).toBe(en.chat.toast.deleted)
    expect(text('.toast-action')).toBe(en.chat.toast.undo)
    setLocale('tr')
    await flush()
    expect(text('.toast-text')).toBe(tr.chat.toast.deleted)
    expect(text('.toast-action')).toBe(tr.chat.toast.undo)
  })

  it('moves focus to Undo when the toast opens, but not when only the language changes', async () => {
    vi.mocked(listConversations).mockResolvedValue([
      { id: 'a', title: 'Sudan access', updated_at: new Date().toISOString() },
    ])
    await mount()
    host.querySelectorAll('.conv-action')[1].click()
    await flush()
    expect(document.activeElement).toBe(host.querySelector('.toast-action'))

    // The user moves to the language switcher and picks Turkish inside the undo window.
    const switcher = host.querySelector('.lang-btn')
    switcher.focus()
    setLocale('tr')
    await flush()
    expect(text('.toast-text')).toBe(tr.chat.toast.deleted)
    expect(document.activeElement).toBe(switcher)
  })

  it('renders the empty state, sidebar and date groups in Turkish', async () => {
    vi.mocked(listConversations).mockResolvedValue([
      { id: 'a', title: 'Sudan access', updated_at: new Date().toISOString() },
    ])
    setLocale('tr')
    await mount()
    expect(text('.empty-title')).toBe(tr.chat.empty.title)
    expect(text('.new-chat-btn')).toBe(tr.chat.newChat)
    expect(text('.conv-section-label')).toBe(tr.chat.groups.today)
    // A stored conversation title is data and is never translated.
    expect(text('.conv-select')).toBe('Sudan access')
    expect(host.querySelector('.conv-search input').placeholder).toBe(tr.chat.search)
    const prompts = [...host.querySelectorAll('.prompt-row')].map((b) => b.textContent.trim())
    expect(prompts).toEqual(Object.values(tr.chat.empty.prompts))
  })
})

// The open conversation lives in the URL (/app?c=<id>), so a reload reopens it.
describe('ChatView keeps the open conversation in the URL', () => {
  const CONVS = [
    { id: 'c1', title: 'Sudan access', updated_at: new Date().toISOString() },
    { id: 'c2', title: 'Yemen cholera', updated_at: new Date().toISOString() },
  ]
  beforeEach(() => {
    setLocale('en')
    vi.mocked(listConversations).mockReset().mockResolvedValue(CONVS)
    vi.mocked(getMessages)
      .mockReset()
      .mockResolvedValue([{ id: 1, role: 'user', content: 'Cholera in Yemen?', sources: null }])
  })
  afterEach(() => {
    app.unmount()
    host.remove()
  })
  const query = () => router.currentRoute.value.query

  it('opens the conversation the URL names, as after a reload', async () => {
    await mount('/app?c=c2')
    expect(getMessages).toHaveBeenCalledWith('c2')
    expect(text('.message.user')).toContain('Cholera in Yemen?')
  })

  it('names the chosen conversation in the URL, and drops it for a new chat', async () => {
    await mount()
    host.querySelectorAll('.conv-select')[0].click()
    await flush()
    expect(query().c).toBe('c1')
    host.querySelector('.new-chat-btn').click()
    await flush()
    expect(query().c).toBeUndefined()
  })

  it('drops a conversation the account does not have', async () => {
    await mount('/app?c=gone')
    expect(query().c).toBeUndefined()
  })

  it('puts the open conversation back in the URL on the way back from another screen', async () => {
    await mount('/app?c=c2')
    await router.push('/reports')
    await flush()
    expect(query().c).toBeUndefined()
    await router.push('/app')
    await flush()
    expect(query().c).toBe('c2')
  })

  it('opens the conversation a link names on the way back', async () => {
    await mount('/app?c=c2')
    await router.push('/reports')
    await router.push('/app?c=c1')
    await flush()
    expect(getMessages).toHaveBeenLastCalledWith('c1')
  })

  it('opens a new chat for a question asked on the landing page', async () => {
    await mount('/app?c=c2')
    expect(text('.message.user')).toContain('Cholera in Yemen?')
    await router.push('/')
    await router.push('/app?q=Sudan%20IDPs')
    await flush()
    expect(query().c).toBeUndefined()
    expect(host.querySelector('.message.user')).toBeNull()
  })

  it('keeps the other query keys', async () => {
    await mount('/app?c=c2&lang=en')
    host.querySelector('.new-chat-btn').click()
    await flush()
    expect(query()).toEqual({ lang: 'en' })
  })
})
