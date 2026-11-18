import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'
import { router } from '../router/index.js'
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
window.scrollTo = () => {}

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
    const types = [...host.querySelectorAll('.report-form select')[0].options].map((o) => o.text)
    expect(types).toEqual(Object.values(tr.reports.types))
    const sectors = [...host.querySelectorAll('.report-form select')[2].options].map((o) => o.text)
    expect(sectors).toEqual([tr.reports.form.allSectors, tr.reports.sectors.health])
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
    expect(text('.saved-name')).toBe('Sudan · Sağlık')
  })

  it('"Run next period" names the report it continues, in the language shown', async () => {
    const q2 = {
      ...SAVED,
      id: 'q2',
      date_from: '2026-05-01',
      date_to: '2026-07-31',
      title: 'Sudan · Health · 2026-05-01 – 2026-07-31',
    }
    vi.mocked(listReports).mockResolvedValue({ reports: [q2] })
    vi.mocked(getReport).mockResolvedValue({ ...q2, content: '## Summary\n\nText.' })
    await mount('/reports?report=q2')
    const run = [...host.querySelectorAll('.pdf-btn')].find(
      (b) => b.textContent.trim() === en.reports.viewer.runNext,
    )
    run.click()
    await flush()
    expect(text('.continues p')).toBe(
      'Continues Sudan · Health, 01.05.2026 - 31.07.2026. The new report opens with what changed since then.',
    )
    // The report language follows the series, not the interface.
    setLocale('tr')
    await flush()
    expect(text('.continues p')).toBe(
      'Sudan · Sağlık (01.05.2026 - 31.07.2026) raporunun devamı. Yeni rapor o dönemden bu yana değişenlerle başlar.',
    )
    expect([...host.querySelectorAll('.report-form select')].at(-1).value).toBe('en')
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
    host.querySelector('.report-form select:nth-of-type(1)')
    const country = host.querySelectorAll('.report-form select')[1]
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
    const country = host.querySelectorAll('.report-form select')[1]
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
