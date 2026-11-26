/* eslint-disable vue/one-component-per-file -- test stand-ins for two screens */
import { describe, it, expect, afterEach, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, ref } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'

const { auth } = await vi.hoisted(async () => {
  const { reactive } = await import('vue')
  return { auth: reactive({ user: { id: 'u1' }, ready: true }) }
})
vi.mock('./utils/authStore.js', () => ({ auth }))

import App from './App.vue'

// Stands in for the chat screen: its state is what a remount would lose.
const ChatView = defineComponent({
  name: 'ChatView',
  setup() {
    const n = ref(0)
    return () => h('button', { id: 'chat', onClick: () => n.value++ }, String(n.value))
  },
})
const Reports = defineComponent({ name: 'ReportsView', render: () => h('p', 'reports') })

let app
let host

async function mount() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/app', component: ChatView },
      { path: '/reports', component: Reports },
      { path: '/', component: { render: () => null } },
    ],
  })
  router.push('/app')
  await router.isReady()
  host = document.createElement('div')
  document.body.appendChild(host)
  app = createApp(App).use(router)
  app.mount(host)
  await nextTick()
  return router
}

const chatText = () => host.querySelector('#chat')?.textContent

describe('App keeps the chat screen across screens', () => {
  afterEach(() => {
    app?.unmount()
    host?.remove()
    auth.user = { id: 'u1' }
  })

  it('returns from Reports to the same chat, not a new one', async () => {
    const router = await mount()
    host.querySelector('#chat').click()
    await nextTick()
    expect(chatText()).toBe('1')

    await router.push('/reports')
    expect(chatText()).toBeUndefined()
    await router.push('/app')
    expect(chatText()).toBe('1')
  })

  it('drops the kept chat when the user signs out', async () => {
    const router = await mount()
    host.querySelector('#chat').click()
    await nextTick()

    auth.user = null
    await router.push('/')
    auth.user = { id: 'u2' }
    await router.push('/app')
    expect(chatText()).toBe('0')
  })
})
