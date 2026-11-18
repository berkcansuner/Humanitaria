import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { createApp, nextTick } from 'vue'
import SuggestionCardIsland from './SuggestionCardIsland.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'
import en from '../locales/en.json'
import tr from '../locales/tr.json'

let app
let host

const clarification = { suggestions: { countries: ['Sudan', 'Syria'], themes: ['Health'] } }

async function settle() {
  for (let i = 0; i < 5; i++) {
    await new Promise((r) => setTimeout(r))
    await nextTick()
  }
}
const title = () => host.querySelector('.sc-title')?.textContent
const input = () => host.querySelector('.sc-input')

describe('SuggestionCardIsland labels', () => {
  beforeEach(async () => {
    localStorage.clear()
    setLocale('en')
    host = document.createElement('div')
    document.body.appendChild(host)
    app = createApp(SuggestionCardIsland, { clarification })
    app.use(i18n)
    app.mount(host)
    await settle()
  })
  afterEach(() => {
    app.unmount()
    host.remove()
    localStorage.clear()
    setLocale('en')
  })

  it('passes every string in from Vue and re-renders the island on a language switch', async () => {
    expect(title()).toBe(en.chat.suggest.country.title)
    expect(input().placeholder).toBe(en.chat.suggest.country.placeholder)
    expect(host.querySelector('.sc-skip').textContent).toBe(en.chat.suggest.skip)

    // Text typed into the card survives the switch (no reset of the step).
    const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
    setValue.call(input(), 'Su')
    input().dispatchEvent(new Event('input', { bubbles: true }))
    await settle()

    setLocale('tr')
    await settle()
    expect(title()).toBe(tr.chat.suggest.country.title)
    expect(input().placeholder).toBe(tr.chat.suggest.country.placeholder)
    expect(host.querySelector('.sc-card').getAttribute('aria-label')).toBe(tr.chat.suggest.card)
    expect(host.querySelector('.sc-skip').textContent).toBe(tr.chat.suggest.skip)
    expect(host.querySelector('.sc-hint').textContent).toBe('1 / 2')
    expect(input().value).toBe('Su')
    // Suggested values come from the server and stay as they are.
    expect(host.querySelector('.sc-ac-item').textContent).toBe('Sudan')
  })
})
