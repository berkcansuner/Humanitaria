import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { createApp, nextTick } from 'vue'
import LanguageSwitcher from './LanguageSwitcher.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'

let app
let host

function mount(props = {}) {
  host = document.createElement('div')
  document.body.appendChild(host)
  app = createApp(LanguageSwitcher, props)
  app.use(i18n)
  app.mount(host)
}

const button = () => host.querySelector('button')
const listbox = () => host.querySelector('[role="listbox"]')
const options = () => [...host.querySelectorAll('[role="option"]')]
const key = (el, k) =>
  el.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }))

async function open() {
  button().click()
  await nextTick()
  await nextTick()
}

describe('LanguageSwitcher', () => {
  beforeEach(() => {
    localStorage.clear()
    setLocale('en')
    mount({ variant: 'app' })
  })
  afterEach(() => {
    app.unmount()
    host.remove()
    localStorage.clear()
    setLocale('en')
  })

  it('shows the current code and an accessible name', () => {
    expect(button().textContent).toContain('EN')
    expect(button().getAttribute('aria-haspopup')).toBe('listbox')
    expect(button().getAttribute('aria-expanded')).toBe('false')
    expect(button().getAttribute('aria-label')).toBe('Language: English')
  })

  it('opens a listbox with two options carrying lang attributes', async () => {
    await open()
    expect(button().getAttribute('aria-expanded')).toBe('true')
    expect(options().map((o) => o.getAttribute('lang'))).toEqual(['en', 'tr'])
    expect(options().map((o) => o.textContent.trim())).toEqual(['English', 'Türkçe'])
  })

  it('marks the current option with aria-selected', async () => {
    await open()
    expect(options().map((o) => o.getAttribute('aria-selected'))).toEqual(['true', 'false'])
  })

  it('ArrowDown then Enter selects Türkçe', async () => {
    await open()
    key(listbox(), 'ArrowDown')
    await nextTick()
    key(listbox(), 'Enter')
    await nextTick()
    expect(i18n.global.locale.value).toBe('tr')
    expect(document.documentElement.lang).toBe('tr')
    expect(localStorage.getItem('lang')).toBe('tr')
    expect(listbox()).toBeNull()
    expect(document.activeElement).toBe(button())
    expect(button().getAttribute('aria-label')).toBe('Dil: Türkçe')
  })

  it('announces the change in the new language', async () => {
    await open()
    options()[1].click()
    await nextTick()
    const live = host.querySelector('[aria-live="polite"]')
    expect(live.textContent).toContain('Türkçe')
    expect(live.textContent).not.toContain('Language')
  })

  it('Escape closes and returns focus to the button', async () => {
    await open()
    key(listbox(), 'Escape')
    await nextTick()
    expect(listbox()).toBeNull()
    expect(document.activeElement).toBe(button())
  })

  it('a click outside closes it', async () => {
    await open()
    document.body.click()
    await nextTick()
    expect(listbox()).toBeNull()
  })
})
