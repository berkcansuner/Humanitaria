import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import Chat from './Chat.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'
import en from '../locales/en.json'
import tr from '../locales/tr.json'

vi.mock('../utils/authStore.js', () => ({ handleSessionExpired: vi.fn() }))

// A /chat/stream response whose SSE frames are pushed by the test, so the
// answer can be held mid-stream while the language changes.
function streamingResponse() {
  const enc = new TextEncoder()
  const waiting = []
  const queued = []
  const reader = {
    read: () =>
      queued.length ? Promise.resolve(queued.shift()) : new Promise((r) => waiting.push(r)),
  }
  const push = (chunk) => (waiting.length ? waiting.shift()(chunk) : queued.push(chunk))
  return {
    res: { ok: true, status: 200, body: { getReader: () => reader } },
    send: (event, data) =>
      push({
        done: false,
        value: enc.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`),
      }),
    end: () => push({ done: true, value: undefined }),
  }
}

let app
let host
let mounts

async function mountChat() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/app', component: Chat }],
  })
  router.push('/app')
  await router.isReady()
  host = document.createElement('div')
  document.body.appendChild(host)
  mounts = 0
  app = createApp(Chat, { conversationId: null })
  // Count Chat mounts: a remount on a language switch would lose the stream.
  app.mixin({
    mounted() {
      if (this.$options.__name === 'Chat') mounts += 1
    },
  })
  app.use(router).use(i18n)
  app.mount(host)
  await nextTick()
}

const flush = async () => {
  for (let i = 0; i < 4; i++) {
    await new Promise((r) => setTimeout(r))
    await nextTick()
  }
}
const textarea = () => host.querySelector('.chat-input')
const answer = () => host.querySelector('.message.assistant .message-content')?.textContent

async function type(text) {
  textarea().value = text
  textarea().dispatchEvent(new Event('input'))
  await nextTick()
}

describe('Chat across a language switch', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setLocale('en')
    document.body.innerHTML = ''
  })
  afterEach(() => {
    app?.unmount()
    host?.remove()
    vi.unstubAllGlobals()
    localStorage.clear()
    setLocale('en')
  })

  it('keeps the streamed answer and the composer text, and does not remount Chat', async () => {
    const stream = streamingResponse()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(stream.res))
    await mountChat()

    await type('Sudan IDPs')
    host.querySelector('form').dispatchEvent(new Event('submit', { cancelable: true }))
    await flush()
    stream.send('token', { content: 'Half of the ' })
    await flush()
    expect(answer()).toContain('Half of the')

    // The user drafts the next question while the answer is still streaming.
    await type('next question')
    const composer = textarea()
    const bubble = host.querySelector('.message.assistant')
    expect(host.querySelector('.stop-btn').getAttribute('aria-label')).toBe(en.chat.composer.stop)

    setLocale('tr')
    await flush()

    expect(host.querySelector('.stop-btn').getAttribute('aria-label')).toBe(tr.chat.composer.stop)
    expect(mounts).toBe(1)
    expect(textarea()).toBe(composer)
    expect(host.querySelector('.message.assistant')).toBe(bubble)
    expect(textarea().value).toBe('next question')
    expect(answer()).toContain('Half of the')

    stream.send('token', { content: 'answer.' })
    stream.end()
    await flush()
    expect(answer()).toContain('Half of the answer.')
    expect(textarea().value).toBe('next question')
  })

  it('keeps exactly one translated copy button per code block after a language switch', async () => {
    const stream = streamingResponse()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(stream.res))
    await mountChat()
    await type('Show the query')
    host.querySelector('form').dispatchEvent(new Event('submit', { cancelable: true }))
    await flush()
    // Citation chips make the rendered HTML depend on the locale (their aria-labels),
    // so the switch re-renders the answer and drops injected buttons.
    stream.send('token', {
      content: 'Run this [1].\n\n```\nprint(1)\n```\n\nThen this:\n\n```\nx = 2\n```\n',
    })
    stream.send('sources', {
      sources: [
        {
          index: 1,
          title: 'Bulletin',
          url: 'https://reliefweb.int/r/1',
          source: 'WHO',
          date: '2026-10-09',
        },
      ],
    })
    stream.end()
    await flush()

    const answerEl = () => host.querySelector('.message.assistant .message-content')
    const buttonsPerPre = () =>
      [...answerEl().querySelectorAll('pre')].map(
        (pre) => pre.querySelectorAll('.copy-code').length,
      )
    expect(answerEl().querySelector('.cite').getAttribute('aria-label')).toContain('Source 1')
    expect(buttonsPerPre()).toEqual([1, 1])
    expect(answerEl().querySelector('.copy-code').getAttribute('aria-label')).toBe(
      en.chat.code.label,
    )

    setLocale('tr')
    await flush()
    expect(answerEl().querySelector('.cite').getAttribute('aria-label')).toContain('Kaynak 1')
    expect(buttonsPerPre()).toEqual([1, 1])
    for (const btn of answerEl().querySelectorAll('.copy-code')) {
      expect(btn.textContent).toBe(tr.chat.code.copy)
      expect(btn.getAttribute('aria-label')).toBe(tr.chat.code.label)
    }

    setLocale('en')
    await flush()
    expect(buttonsPerPre()).toEqual([1, 1])
    expect(answerEl().querySelector('.copy-code').textContent).toBe(en.chat.code.copy)
  })

  it('translates an SSE error event by its code and follows a language switch', async () => {
    const stream = streamingResponse()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(stream.res))
    await mountChat()
    await type('Sudan')
    host.querySelector('form').dispatchEvent(new Event('submit', { cancelable: true }))
    await flush()
    stream.send('error', { code: 'model_busy', message: 'The model is busy.' })
    stream.end()
    await flush()
    const banner = () => host.querySelector('.error-text').textContent.trim()
    expect(banner()).toBe(en.errors.model_busy)
    setLocale('tr')
    await flush()
    expect(banner()).toBe(tr.errors.model_busy)
  })

  it('shows the generic message for an SSE error with a code this client does not know', async () => {
    const stream = streamingResponse()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(stream.res))
    await mountChat()
    await type('Sudan')
    host.querySelector('form').dispatchEvent(new Event('submit', { cancelable: true }))
    await flush()
    stream.send('error', { code: 'future_code', message: 'Something new.' })
    stream.end()
    await flush()
    expect(host.querySelector('.error-text').textContent.trim()).toBe(en.errors.generic)
  })

  it('keeps a connection failure as a key, so the banner follows the language', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await mountChat()
    await type('Sudan')
    host.querySelector('form').dispatchEvent(new Event('submit', { cancelable: true }))
    await flush()
    const banner = () => host.querySelector('.error-text').textContent.trim()
    expect(banner()).toBe(en.chat.errors.connection)
    setLocale('tr')
    await flush()
    expect(banner()).toBe(tr.chat.errors.connection)
  })
})
