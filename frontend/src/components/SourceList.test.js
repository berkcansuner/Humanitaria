import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { createApp, nextTick } from 'vue'
import SourceList from './SourceList.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'

let app
let host
async function mount(sources) {
  host = document.createElement('div')
  document.body.appendChild(host)
  app = createApp(SourceList, { sources })
  app.use(i18n)
  app.mount(host)
  await nextTick()
}
const metas = () => [...host.querySelectorAll('.source-meta')].map((m) => m.textContent.trim())

describe('SourceList', () => {
  beforeEach(() => {
    localStorage.clear()
    setLocale('en')
  })
  afterEach(() => {
    app.unmount()
    host.remove()
    setLocale('en')
  })

  it('keeps the publisher and country line for a report source', async () => {
    await mount([
      {
        index: 1,
        title: 'Sudan Access Update',
        url: 'https://reliefweb.int/report/1',
        source: 'OCHA',
        country: 'Sudan',
        date: '2026-10-21',
      },
    ])
    expect(metas()).toEqual(['OCHA · Sudan'])
  })

  it('renders nothing without sources', async () => {
    await mount(null)
    expect(host.querySelector('.sources')).toBeNull()
  })
})
