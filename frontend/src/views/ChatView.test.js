import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import ChatView from './ChatView.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'
import { listConversations } from '../utils/api.js'
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

async function mount() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/app', component: ChatView },
      { path: '/:rest(.*)*', component: { render: () => null } },
    ],
  })
  router.push('/app')
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
