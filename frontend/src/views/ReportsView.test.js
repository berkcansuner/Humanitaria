import { describe, it, expect, beforeAll, afterAll, beforeEach, afterEach, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'
import { router } from '../router/index.js'
import App from '../App.vue'
import { getReportOptions, listReports, getReport } from '../utils/reportsApi.js'
import en from '../locales/en.json'
import tr from '../locales/tr.json'

vi.mock('../utils/reportsApi.js', () => ({
  getReportOptions: vi.fn(),
  listReports: vi.fn(),
  getReport: vi.fn(),
  deleteReport: vi.fn(),
}))
vi.mock('../utils/authStore.js', () => ({
  auth: { user: { name: 'Demo User', email: 'demo@example.org' }, ready: true },
  refresh: vi.fn(),
  isAuthenticated: () => true,
  isAdmin: () => false,
  doLogout: vi.fn(),
  handleSessionExpired: vi.fn(),
}))

const SAVED = {
  id: 'r1',
  report_type: 'situation',
  country: 'Sudan',
  theme: 'Health',
  date_from: '2026-08-01',
  date_to: '2026-10-31',
  language: 'en',
  title: 'Sudan · Health · 2026-08-01 – 2026-10-31',
  previous_report_id: null,
  created_at: '2026-11-01T09:00:00',
}

// jsdom has no scrolling; the router's scrollBehavior calls it on every navigation.
const realScrollTo = window.scrollTo
beforeAll(() => {
  window.scrollTo = () => {}
})
afterAll(() => {
  window.scrollTo = realScrollTo
})

let app
let host

// The real router: it re-applies the route's tab title on every language change.
async function mount(path = '/reports') {
  await router.push(path)
  await router.isReady()
  host = document.createElement('div')
  document.body.appendChild(host)
  app = createApp({ template: '<router-view />' })
  app.use(router).use(i18n)
  app.mount(host)
  await flush()
}

const flush = async () => {
  for (let i = 0; i < 4; i++) {
    await new Promise((r) => setTimeout(r))
    await nextTick()
  }
}
const text = (sel) => host.querySelector(sel)?.textContent.trim()
// The report type is a radio group; country, sector and language are selects.
const chooseType = async (value) => {
  host.querySelector(`.type-radio[value="${value}"]`).click()
  await flush()
}

describe('ReportsView in two languages', () => {
  beforeEach(() => {
    localStorage.clear()
    setLocale('en')
    vi.mocked(getReportOptions).mockResolvedValue({ countries: ['Sudan'], themes: ['Health'] })
    vi.mocked(listReports).mockResolvedValue({ reports: [] })
    vi.mocked(getReport).mockReset()
  })
  afterEach(async () => {
    app.unmount()
    host.remove()
    vi.unstubAllGlobals()
    localStorage.clear()
    setLocale('en')
    await router.push('/')
  })

  it('opens the report form in the interface language', async () => {
    setLocale('tr')
    await mount()
    expect(host.querySelector('.report-form select:last-of-type')).toBeTruthy()
    const language = [...host.querySelectorAll('.report-form select')].at(-1)
    expect(language.value).toBe('tr')
    expect(text('.form-title')).toBe(tr.reports.form.title)
  })

  it('opens the form behind "New report" in the language chosen since the page loaded', async () => {
    vi.mocked(listReports).mockResolvedValue({ reports: [SAVED] })
    await mount()
    setLocale('tr')
    await flush()
    host.querySelector('.new-report-btn').click()
    await flush()
    const language = [...host.querySelectorAll('.report-form select')].at(-1)
    expect(language.value).toBe('tr')
    // Report types and sectors are named in the interface language.
    const types = [...host.querySelectorAll('.type-name')].map((o) => o.textContent.trim())
    expect(types).toEqual(Object.values(tr.reports.types))
    const descriptions = [...host.querySelectorAll('.type-desc')].map((o) => o.textContent.trim())
    expect(descriptions).toEqual(Object.values(tr.reports.typeDescriptions))
    const sectors = [...host.querySelectorAll('.report-form select')[1].options].map((o) => o.text)
    expect(sectors).toEqual([tr.reports.form.allSectors, tr.reports.sectors.health])
  })

  it('"New report" closes the open report and puts the form in its place', async () => {
    vi.mocked(listReports).mockResolvedValue({ reports: [SAVED] })
    vi.mocked(getReport).mockResolvedValue({ ...SAVED, content: '## Summary\n\nText.' })
    await mount('/reports?report=r1')
    expect(host.querySelector('.report-form')).toBeNull()
    host.querySelector('.new-report-btn').click()
    await flush()
    expect(host.querySelector('.report-content')).toBeNull()
    expect(host.querySelector('.report-main .report-form')).toBeTruthy()
    expect(router.currentRoute.value.query.report).toBeUndefined()
    expect(document.activeElement.classList.contains('form-title')).toBe(true)
  })

  it('offers copy and PDF on an open report, and no series actions', async () => {
    vi.mocked(listReports).mockResolvedValue({ reports: [SAVED] })
    vi.mocked(getReport).mockResolvedValue({ ...SAVED, content: '## Summary\n\nText.' })
    await mount('/reports?report=r1')
    const actions = [...host.querySelectorAll('.report-actions button')].map((b) =>
      b.textContent.trim(),
    )
    expect(actions).toEqual([en.reports.viewer.copy, en.reports.viewer.pdf])
  })

  it("keeps the open report's tab title through a language switch", async () => {
    vi.mocked(listReports).mockResolvedValue({ reports: [SAVED] })
    vi.mocked(getReport).mockResolvedValue({ ...SAVED, content: '## Summary\n\nText.' })
    await mount('/reports?report=r1')
    expect(document.title).toBe('Sudan · Situation Report · Humanitaria')
    setLocale('tr')
    await flush()
    expect(document.title).toBe('Sudan · Durum raporu · Humanitaria')
  })

  it('names type and sector in the interface language, the report body in its own', async () => {
    vi.mocked(listReports).mockResolvedValue({ reports: [SAVED] })
    vi.mocked(getReport).mockResolvedValue({ ...SAVED, content: '## Summary\n\nText.' })
    setLocale('tr')
    await mount('/reports?report=r1')
    const meta = [...host.querySelectorAll('.report-meta .meta-part')].map((m) => m.textContent)
    expect(meta).toEqual(['Durum raporu', 'Sağlık', '01.08.2026 - 31.10.2026'])
    expect(host.querySelector('.report-content').getAttribute('lang')).toBe('en')
    expect(text('.saved-name')).toBe('Sudan')
    expect(text('.saved-sector')).toBe('Sağlık')
  })

  it('names a saved row in full in its tooltip, in the interface language', async () => {
    const yemen = {
      ...SAVED,
      id: 'y1',
      report_type: 'needs_assessment',
      country: 'Yemen',
      theme: 'Shelter and Non-Food Items',
      date_from: '2026-07-01',
      date_to: '2026-09-30',
      title:
        'Needs Assessment Brief — Yemen · Shelter and Non-Food Items · 2026-07-01 – 2026-09-30',
    }
    vi.mocked(listReports).mockResolvedValue({ reports: [yemen] })
    await mount()
    const tooltip = () => host.querySelector('.saved-open').getAttribute('title')
    // English keeps the stored title exactly as before.
    expect(tooltip()).toBe(yemen.title)
    setLocale('tr')
    await flush()
    expect(tooltip()).toBe(
      'Yemen · Barınma ve gıda dışı malzemeler · 01.07.2026 - 30.09.2026 · Rapor dili: İngilizce',
    )
    setLocale('en')
    await flush()
    expect(tooltip()).toBe(yemen.title)
  })

  it('names a saved report from its fields when its title has no period', async () => {
    const sudan = {
      ...SAVED,
      id: 't0',
      report_type: 'indicator_monitoring',
      theme: null,
      date_from: '2025-11-19',
      date_to: '2026-11-19',
      title: 'Indicator Monitoring Report — Sudan · All sectors',
    }
    vi.mocked(listReports).mockResolvedValue({ reports: [sudan] })
    vi.mocked(getReport).mockResolvedValue({ ...sudan, content: '## Summary\n\nText.' })
    await mount('/reports?report=t0')
    expect(text('.saved-name')).toBe('Sudan')
    expect(text('.saved-period')).toBe('19.11.2025 - 19.11.2026')
    expect(text('.report-title-h')).toBe('Sudan')
    const meta = [...host.querySelectorAll('.report-meta .meta-part')].map((m) => m.textContent)
    expect(meta).toEqual(['Indicator Monitoring Report', '19.11.2025 - 19.11.2026'])
  })

  describe("the saved list shows each report's language", () => {
    const syria = {
      ...SAVED,
      report_type: 'needs_assessment',
      country: 'Syrian Arab Republic',
      theme: null,
      date_from: '2025-11-18',
      date_to: '2026-11-18',
      title:
        'Needs Assessment Brief — Syrian Arab Republic · All sectors · 2025-11-18 – 2026-11-18',
    }
    const twins = [
      { ...syria, id: 'syr-en', language: 'en' },
      { ...syria, id: 'syr-tr', language: 'tr' },
    ]
    // The list keeps the order it was given (newest first).
    const rowOf = (id) => host.querySelectorAll('.saved-item')[twins.findIndex((r) => r.id === id)]
    const code = (li) => li.querySelector('.saved-lang-code')?.textContent.trim()
    const spoken = (li) => li.querySelector('.saved-lang .sr-only')?.textContent.trim()

    it('tells two otherwise identical reports apart by their language code', async () => {
      vi.mocked(listReports).mockResolvedValue({ reports: twins })
      await mount()
      expect(code(rowOf('syr-en'))).toBe('EN')
      expect(code(rowOf('syr-tr'))).toBe('TR')
      // The code sits in the meta line, which never truncates, not in the name.
      expect(rowOf('syr-tr').querySelector('.saved-meta .saved-lang')).toBeTruthy()
      expect(rowOf('syr-tr').querySelector('.saved-name .saved-lang')).toBeNull()
    })

    it('names the language in the interface language and follows a switch', async () => {
      vi.mocked(listReports).mockResolvedValue({ reports: twins })
      await mount()
      expect(spoken(rowOf('syr-en'))).toBe('Report language: English')
      expect(spoken(rowOf('syr-tr'))).toBe('Report language: Turkish')
      expect(rowOf('syr-tr').querySelector('.saved-lang-code').getAttribute('aria-hidden')).toBe(
        'true',
      )
      setLocale('tr')
      await flush()
      expect(spoken(rowOf('syr-en'))).toBe('Rapor dili: İngilizce')
      expect(spoken(rowOf('syr-tr'))).toBe('Rapor dili: Türkçe')
      // The code itself is the same in every interface language.
      expect(code(rowOf('syr-tr'))).toBe('TR')
    })

    it('shows another language the same way, and nothing when the language is unknown', async () => {
      vi.mocked(listReports).mockResolvedValue({
        reports: [
          { ...syria, id: 'fr', language: 'fr' },
          { ...syria, id: 'none', country: 'Haiti', language: null },
          { ...syria, id: 'blank', country: 'Chad', language: '' },
          { ...syria, id: 'junk', country: 'Mali', language: 'not a code' },
        ],
      })
      await mount()
      const items = [...host.querySelectorAll('.saved-item')]
      expect(code(items[0])).toBe('FR')
      expect(spoken(items[0])).toBe('Report language: French')
      for (const li of items.slice(1)) expect(li.querySelector('.saved-lang')).toBeNull()
    })

    it('puts the language in the Turkish tooltip, and keeps the English one as stored', async () => {
      vi.mocked(listReports).mockResolvedValue({ reports: twins })
      await mount()
      const tip = (id) => rowOf(id).querySelector('.saved-open').getAttribute('title')
      expect(tip('syr-tr')).toBe(syria.title)
      setLocale('tr')
      await flush()
      expect(tip('syr-tr')).toBe(
        'Syrian Arab Republic · 18.11.2025 - 18.11.2026 · Rapor dili: Türkçe',
      )
    })
  })

  describe('the saved list names each type', () => {
    const q2 = {
      ...SAVED,
      id: 'q2',
      date_from: '2026-05-01',
      date_to: '2026-07-31',
      title: 'Sudan · Health · 2026-05-01 – 2026-07-31',
    }
    const yemen = {
      ...SAVED,
      id: 'y1',
      report_type: 'indicator_monitoring',
      country: 'Yemen',
      theme: null,
      title: 'Indicator Monitoring Report — Yemen · All sectors · 2026-08-01 – 2026-10-31',
    }
    const somalia = {
      ...SAVED,
      id: 's1',
      report_type: 'needs_assessment',
      country: 'Somalia',
      theme: null,
      title: 'Needs Assessment Brief — Somalia · All sectors · 2026-08-01 – 2026-10-31',
    }
    // The meta line's first row (the type and language), without the screen-reader-only
    // language name; NBSPs read as spaces.
    const typeLine = (el) => {
      const row = el.querySelector('.saved-meta > span').cloneNode(true)
      row.querySelectorAll('.sr-only').forEach((s) => s.remove())
      return row.textContent.replace(/\s+/g, ' ').trim()
    }

    it('shows the full type in every row, in both languages', async () => {
      vi.mocked(listReports).mockResolvedValue({ reports: [SAVED, yemen, somalia] })
      await mount()
      const rows = [...host.querySelectorAll('.saved-list > .saved-item')]
      expect(rows.map(typeLine)).toEqual([
        'Situation Report · EN',
        'Indicator Monitoring Report · EN',
        'Needs Assessment · EN',
      ])
      setLocale('tr')
      await flush()
      expect(rows.map(typeLine)).toEqual([
        'Durum raporu · EN',
        'Gösterge izleme raporu · EN',
        'İhtiyaç değerlendirmesi · EN',
      ])
      // The delete button names the type in full too.
      expect(rows[1].querySelector('.saved-del').getAttribute('aria-label')).toBe(
        'Raporu sil: Yemen, Gösterge izleme raporu, 01.08.2026 - 31.10.2026',
      )
    })

    it('lists reports with the same settings one by one, newest first', async () => {
      vi.mocked(listReports).mockResolvedValue({ reports: [SAVED, q2] })
      await mount()
      const rows = [...host.querySelectorAll('.saved-list > .saved-item')]
      expect(rows.map((r) => r.querySelector('.saved-period').textContent.trim())).toEqual([
        '01.08.2026 - 31.10.2026',
        '01.05.2026 - 31.07.2026',
      ])
      expect(host.querySelector('.saved-series-head')).toBeNull()
    })

    it('never starts a line of the meta with a separator', async () => {
      vi.mocked(listReports).mockResolvedValue({ reports: [SAVED, q2, yemen] })
      await mount()
      // The period sits on its own line under the type: no leading "·".
      expect(text('.saved-period')).toBe('01.08.2026 - 31.10.2026')
      // A wrap may only fall after a separator, never just before one: each "·" is
      // glued to the word in front of it by a no-break space.
      for (const meta of host.querySelectorAll('.saved-meta')) {
        expect(meta.textContent).not.toMatch(/[ \n\t]·/)
      }
    })
  })

  it('opens the source a chip in an Indicator Table cell points to', async () => {
    const report = {
      ...SAVED,
      report_type: 'indicator_monitoring',
      content:
        '## Indicator Table\n\n| Indicator | Latest value | As of |\n| --- | --- | --- |\n| IDPs | 3.1 million [2] | 31 January 2026 |',
      sources: [1, 2].map((n) => ({
        index: n,
        title: `Source ${n}`,
        url: `https://reliefweb.int/report/${n}`,
        source: 'OCHA',
        date: '2026-01-31',
      })),
    }
    vi.mocked(listReports).mockResolvedValue({ reports: [report] })
    vi.mocked(getReport).mockResolvedValue(report)
    await mount('/reports?report=r1')
    Element.prototype.scrollIntoView = () => {}
    const chip = host.querySelector('.report-content td a.cite')
    expect(chip.textContent).toBe('2')
    chip.click()
    await flush()
    delete Element.prototype.scrollIntoView
    expect(host.querySelector('.source-item.active').getAttribute('data-srcid')).toBe('2')
  })

  describe('while a report is being prepared', () => {
    // A stream the test feeds by hand: push() delivers one SSE event.
    function stubStream() {
      const queue = []
      let wake = null
      const enc = new TextEncoder()
      const reader = {
        read: () =>
          new Promise((resolve) => {
            const next = () => (queue.length ? resolve(queue.shift()) : (wake = next))
            next()
          }),
      }
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, body: { getReader: () => reader } }),
      )
      const deliver = (item) => {
        queue.push(item)
        if (wake) {
          const w = wake
          wake = null
          w()
        }
      }
      return {
        push: (event, data) =>
          deliver({
            done: false,
            value: enc.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`),
          }),
      }
    }
    async function start({ type = 'situation', theme = 'Health' } = {}) {
      await chooseType(type)
      const [country, sector] = host.querySelectorAll('.report-form select')
      country.value = 'Sudan'
      country.dispatchEvent(new Event('change'))
      sector.value = theme
      sector.dispatchEvent(new Event('change'))
      await flush()
      host.querySelector('.report-form').dispatchEvent(new Event('submit'))
      await flush()
    }
    const seconds = async (s) => {
      vi.advanceTimersByTime(s * 1000)
      await flush()
    }
    // The request line glues each "·" to the part before it with a no-break space.
    const request = () => text('.progress-request')?.replace(/\s+/g, ' ')
    const stage = () => text('.report-progress [role="status"]')
    const outline = () =>
      [...host.querySelectorAll('.progress-outline li')].map((li) => li.textContent.trim())

    beforeEach(() => {
      // The elapsed counter runs on setInterval and Date; flush() keeps real setTimeout.
      vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] })
    })
    afterEach(() => {
      vi.useRealTimers()
    })

    it('shows the request, the stage and the time waited, then hands over to the text', async () => {
      const stream = stubStream()
      vi.mocked(getReport).mockResolvedValue({ ...SAVED, content: '## Summary\n\nText.' })
      await mount()
      await start()
      expect(request()).toMatch(/^Situation Report · Sudan · Health · .+ · English$/)
      expect(stage()).toBe(en.reports.viewer.reading)
      expect(outline()).toEqual(['Executive Summary', 'Key Findings', 'Outlook'])
      expect(text('.progress-elapsed')).toBe('0:00 elapsed')
      // Focus stays on Stop; nothing in the waiting state takes it.
      expect(document.activeElement.classList.contains('stop-gen')).toBe(true)

      await seconds(45)
      expect(text('.progress-elapsed')).toBe('0:45 elapsed')
      // The live region names the stage, never the time.
      expect(stage()).toBe(en.reports.viewer.reading)
      await seconds(75)
      expect(stage()).toBe(en.reports.progress.slow)

      stream.push('token', { content: '## Executive Summary\n\nNeeds rose [12].' })
      await flush()
      // The outline gives way to the text; the request line above it stays put.
      expect(host.querySelector('.progress-outline')).toBeNull()
      expect(text('.report-content h2')).toBe('Executive Summary')
      expect(request()).toMatch(/^Situation Report · Sudan/)
      expect(stage()).toBe(en.reports.progress.writing)

      stream.push('saved', { report_id: 'r1', title: SAVED.title })
      await flush()
      expect(host.querySelector('.report-progress')).toBeNull()
      expect(text('.report-title-h')).toBe('Sudan')
    })

    it('follows a language switch mid-wait without losing the time waited', async () => {
      stubStream()
      await mount()
      await start()
      await seconds(30)
      setLocale('tr')
      await flush()
      expect(request()).toMatch(/^Durum raporu · Sudan · Sağlık · .+ · İngilizce$/)
      expect(stage()).toBe(tr.reports.viewer.reading)
      expect(outline()).toEqual(['Yönetici özeti', 'Temel bulgular', 'Beklentiler'])
      expect(text('.progress-elapsed')).toBe('Geçen süre: 0:30')
      await seconds(5)
      expect(text('.progress-elapsed')).toBe('Geçen süre: 0:35')
    })

    // What the server says it is reading, before the first word (the "status" event).
    const READING = {
      stage: 'reading',
      count: 14,
      sources: [
        { title: 'Sudan: Humanitarian Access Snapshot', source: 'OCHA', date: '2026-10-11' },
        { title: 'IPC Acute Food Insecurity Analysis', source: 'IPC', date: '2026-10-02' },
        { title: 'WFP Sudan Situation Report #42', source: 'WFP', date: null },
      ],
    }
    const rows = () =>
      [...host.querySelectorAll('.progress-read li')].map((li) => [
        li.querySelector('.read-title').textContent.trim(),
        li.querySelector('.read-meta').textContent.trim(),
      ])

    it('names the sources being read once the server lists them', async () => {
      const stream = stubStream()
      await mount()
      await start()
      // Before the event: the general stage, and no list.
      expect(stage()).toBe(en.reports.viewer.reading)
      expect(host.querySelector('.progress-read')).toBeNull()

      stream.push('status', READING)
      await flush()
      expect(stage()).toBe('Reading 14 sources. The first words usually appear within two minutes.')
      expect(text('.progress-read .read-caption')).toBe("Sources in this report's reading list")
      expect(rows()).toEqual([
        ['Sudan: Humanitarian Access Snapshot', 'OCHA · 11.10.2026'],
        ['IPC Acute Food Insecurity Analysis', 'IPC · 02.10.2026'],
        ['WFP Sudan Situation Report #42', 'WFP'],
      ])
      // All rows are in the page at once: the row-by-row reveal is CSS only, so
      // reduced motion shows the same static list.
      expect(host.querySelectorAll('.progress-read li')).toHaveLength(3)
      expect(text('.progress-read .read-more')).toBe('and 11 more')
      // The outline of the sections to come is still there below it.
      expect(outline()).toEqual(['Executive Summary', 'Key Findings', 'Outlook'])

      stream.push('token', { content: '## Executive Summary\n\nNeeds rose [12].' })
      await flush()
      expect(host.querySelector('.progress-read')).toBeNull()
      expect(stage()).toBe(en.reports.progress.writing)
    })

    // Twelve listed of eighteen read: five rows at a time, so the outline and its
    // motion stay in view; the rows turn over slowly through the real list.
    const LONG = {
      stage: 'reading',
      count: 18,
      sources: Array.from({ length: 12 }, (_, i) => ({
        title: `Report ${i + 1}`,
        source: 'OCHA',
        date: '2026-10-01',
      })),
    }
    const titles = () => rows().map((r) => r[0])
    const motion = (reduce) =>
      vi.stubGlobal('matchMedia', (query) => ({
        matches: reduce && query.includes('reduce'),
        media: query,
        addEventListener() {},
        removeEventListener() {},
      }))

    it('shows five sources at a time and turns slowly through the whole list', async () => {
      motion(false)
      const stream = stubStream()
      await mount()
      await start()
      stream.push('status', LONG)
      await flush()
      expect(titles()).toEqual(['Report 1', 'Report 2', 'Report 3', 'Report 4', 'Report 5'])
      // The count stays the same whichever rows are in view.
      expect(text('.progress-read .read-more')).toBe('and 13 more')
      await seconds(6)
      expect(titles()).toEqual(['Report 6', 'Report 7', 'Report 8', 'Report 9', 'Report 10'])
      expect(text('.progress-read .read-more')).toBe('and 13 more')
      await seconds(6)
      // The list wraps round, so every listed source is shown in turn.
      expect(titles()).toEqual(['Report 11', 'Report 12', 'Report 1', 'Report 2', 'Report 3'])
      // The live region named the count once; the turning rows are not announced.
      expect(stage()).toBe('Reading 18 sources. The first words usually appear within two minutes.')
    })

    it('holds the first five still under reduced motion', async () => {
      motion(true)
      const stream = stubStream()
      await mount()
      await start()
      stream.push('status', LONG)
      await flush()
      await seconds(30)
      expect(titles()).toEqual(['Report 1', 'Report 2', 'Report 3', 'Report 4', 'Report 5'])
      expect(text('.progress-read .read-more')).toBe('and 13 more')
    })

    it('keeps the sources through a language switch, titles untranslated', async () => {
      const stream = stubStream()
      await mount()
      await start()
      stream.push('status', READING)
      await flush()
      await seconds(20)
      setLocale('tr')
      await flush()
      expect(stage()).toBe(
        '14 kaynak okunuyor. İlk sözcükler genellikle iki dakika içinde görünür.',
      )
      expect(text('.progress-read .read-caption')).toBe('Bu raporun okuma listesindeki kaynaklar')
      expect(rows()[0]).toEqual(['Sudan: Humanitarian Access Snapshot', 'OCHA · 11.10.2026'])
      expect(text('.progress-read .read-more')).toBe('ve 11 kaynak daha')
      expect(text('.progress-elapsed')).toBe('Geçen süre: 0:20')
    })
  })

  it('shows a generation error in the current language and follows a switch', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ detail: 'Report limit reached', code: 'report_limit' }),
      }),
    )
    await mount()
    const country = host.querySelectorAll('.report-form select')[0]
    country.value = 'Sudan'
    country.dispatchEvent(new Event('change'))
    await flush()
    host.querySelector('.report-form').dispatchEvent(new Event('submit'))
    await flush()
    expect(text('.error-text')).toBe(en.errors.report_limit)
    setLocale('tr')
    await flush()
    expect(text('.error-text')).toBe(tr.errors.report_limit)
  })

  it('translates a streamed error by its code', async () => {
    const chunks = [
      new TextEncoder().encode(
        'event: error\ndata: {"code": "model_busy", "message": "The model is busy"}\n\n',
      ),
    ]
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        body: {
          getReader: () => ({
            read: async () =>
              chunks.length ? { done: false, value: chunks.shift() } : { done: true },
          }),
        },
      }),
    )
    setLocale('tr')
    await mount()
    const country = host.querySelectorAll('.report-form select')[0]
    country.value = 'Sudan'
    country.dispatchEvent(new Event('change'))
    await flush()
    host.querySelector('.report-form').dispatchEvent(new Event('submit'))
    await flush()
    expect(text('.error-text')).toBe(tr.errors.model_busy)
    setLocale('en')
    await flush()
    expect(text('.error-text')).toBe(en.errors.model_busy)
  })
})

// App.vue keeps the reports screen alive while another screen is open, so a
// report being written, or the one open, is still there on the way back.
describe('ReportsView kept alive across screens', () => {
  let push
  beforeEach(() => {
    localStorage.clear()
    setLocale('en')
    vi.mocked(getReportOptions).mockResolvedValue({ countries: ['Sudan'], themes: ['Health'] })
    vi.mocked(listReports).mockResolvedValue({ reports: [] })
    vi.mocked(getReport).mockReset()
  })
  afterEach(async () => {
    app.unmount()
    host.remove()
    vi.unstubAllGlobals()
    await router.push('/')
  })

  async function mountApp(path) {
    await router.push(path)
    await router.isReady()
    host = document.createElement('div')
    document.body.appendChild(host)
    app = createApp(App)
    app.use(router).use(i18n)
    app.mount(host)
    await flush()
  }

  // A report stream the test feeds one SSE event at a time.
  function stubStream() {
    const queue = []
    let wake = null
    push = (event, data) => {
      queue.push(new TextEncoder().encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`))
      wake?.()
    }
    const end = () => {
      queue.push(null)
      wake?.()
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        body: {
          getReader: () => ({
            read: async () => {
              while (!queue.length) await new Promise((r) => (wake = r))
              const value = queue.shift()
              return value ? { done: false, value } : { done: true }
            },
          }),
        },
      }),
    )
    return end
  }

  it('keeps a report being written, and saves it without touching the other screen', async () => {
    const end = stubStream()
    await mountApp('/reports')
    const country = host.querySelectorAll('.report-form select')[0]
    country.value = 'Sudan'
    country.dispatchEvent(new Event('change'))
    await flush()
    host.querySelector('.report-form').dispatchEvent(new Event('submit'))
    await flush()
    push('token', { content: '## Summary\n\nDisplacement rose.' })
    await flush()

    await router.push('/privacy')
    await flush()
    vi.mocked(getReport).mockResolvedValue({ ...SAVED, id: 'r9', content: '## Summary\n\nSaved.' })
    vi.mocked(listReports).mockResolvedValue({ reports: [{ ...SAVED, id: 'r9' }] })
    push('saved', { report_id: 'r9', title: SAVED.title })
    end()
    await flush()
    expect(router.currentRoute.value.fullPath).toBe('/privacy')
    expect(document.title).not.toContain('Situation Report')

    await router.push('/reports')
    await flush()
    expect(router.currentRoute.value.query.report).toBe('r9')
    expect(text('.report-content')).toContain('Saved.')
  })

  it('reopens the report that was open', async () => {
    vi.mocked(listReports).mockResolvedValue({ reports: [SAVED] })
    vi.mocked(getReport).mockResolvedValue({ ...SAVED, content: '## Summary\n\nText.' })
    await mountApp('/reports?report=r1')
    await router.push('/privacy')
    await flush()
    await router.push('/reports')
    await flush()
    expect(router.currentRoute.value.query.report).toBe('r1')
    expect(text('.report-content')).toContain('Text.')
    expect(document.title).toBe('Sudan · Situation Report · Humanitaria')
  })

  it('opens the report a link names when coming back', async () => {
    vi.mocked(listReports).mockResolvedValue({ reports: [SAVED, { ...SAVED, id: 'r2' }] })
    vi.mocked(getReport).mockImplementation(async (id) => ({
      ...SAVED,
      id,
      content: `## Summary\n\nReport ${id}.`,
    }))
    await mountApp('/reports?report=r1')
    await router.push('/privacy')
    await flush()
    await router.push('/reports?report=r2')
    await flush()
    expect(text('.report-content')).toContain('Report r2.')
  })
})
