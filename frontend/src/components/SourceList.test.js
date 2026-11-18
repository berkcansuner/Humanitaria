import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { createApp, nextTick } from 'vue'
import SourceList from './SourceList.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'

// A technical monitoring report's sources: the HDX HAPI datasets it used.
const IOM_CREDIT =
  'International Organization for Migration (IOM), January 2026, Displacement Tracking Matrix (DTM), https://dtm.iom.int'
const DATASETS = [
  {
    index: 1,
    title: 'Food security: people in need',
    url: 'https://data.humdata.org/dataset/global-hpc-hno',
    source: 'OCHA HNO',
    date: '2026-01-01',
    country: 'Afghanistan',
    doctype: 'dataset',
    dataset: 'Global Humanitarian Programme Cycle, Humanitarian Needs',
    period: '2024-01-01 – 2026-01-01',
    retrieved: '2026-11-18',
  },
  {
    index: 2,
    title: 'Internally displaced people (IDPs)',
    url: 'https://data.humdata.org/dataset/afghanistan-displacement-data',
    source: IOM_CREDIT,
    date: '2026-01-31',
    country: 'Afghanistan',
    doctype: 'dataset',
    period: '2026-01-31',
    retrieved: '2026-11-18',
  },
]

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

  it('describes a data source by publisher, dataset, period and retrieval date', async () => {
    await mount(DATASETS)
    expect(host.querySelector('.sources-summary').textContent).toContain('2 sources')
    expect(metas()).toEqual([
      'OCHA HNO · Global Humanitarian Programme Cycle, Humanitarian Needs · 2024-01-01 – 2026-01-01 · retrieved 2026-11-18',
      // The IOM DTM credit line is shown whole, exactly as given.
      `${IOM_CREDIT} · 2026-01-31 · retrieved 2026-11-18`,
    ])
    const link = host.querySelector('.source-link')
    expect(link.getAttribute('href')).toBe('https://data.humdata.org/dataset/global-hpc-hno')
    expect(link.textContent.trim()).toBe('Food security: people in need')
  })

  it('names HDX HAPI on the closed line; the credit lines stay whole in the rows', async () => {
    await mount(DATASETS)
    const summary = host.querySelector('.sources-summary').textContent.replace(/\s+/g, ' ')
    // (the gaps between the parts are CSS, not text)
    expect(summary).toMatch(/^2 sources\s*·\s*HDX HAPI\s*·\s*Show$/)
    expect(summary).not.toContain('International Organization for Migration')
  })

  it('writes dates in the interface language and never translates names', async () => {
    setLocale('tr')
    await mount(DATASETS)
    expect(host.querySelector('.sources-summary').textContent).toContain('2 kaynak')
    expect(metas()[0]).toBe(
      'OCHA HNO · Global Humanitarian Programme Cycle, Humanitarian Needs · 1 Oca 2024 – 1 Oca 2026 · erişim tarihi 18 Kas 2026',
    )
    expect(metas()[1].startsWith(IOM_CREDIT)).toBe(true)
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

  it('renders nothing without sources (an older technical report)', async () => {
    await mount(null)
    expect(host.querySelector('.sources')).toBeNull()
  })
})
