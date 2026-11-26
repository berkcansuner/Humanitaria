import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import AdminIngestionView from './AdminIngestionView.vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'
import { getIngestStatus, getIngestDocuments } from '../utils/adminApi.js'

vi.mock('../utils/authStore.js', () => ({
  auth: { user: { id: 'u1', email: 'a@example.org', name: 'Ada', is_admin: true }, ready: true },
  doLogout: vi.fn(),
}))
vi.mock('../utils/authApi.js', () => ({ updateLanguage: vi.fn() }))
vi.mock('../utils/adminApi.js', () => ({
  getIngestStatus: vi.fn(),
  getIngestDocuments: vi.fn(),
  triggerIngest: vi.fn(),
  listUsers: vi.fn(),
}))

let app
let host

function status(source) {
  return {
    last_ingest: '2026-11-18',
    scheduler_active: false,
    chunk_count: 10,
    document_count: 5,
    run: {
      running: false,
      source,
      started_at: '2026-11-18T10:00:00Z',
      finished_at: null,
      last_error: null,
      last_stats: { reports: { total: 1, succeeded: 1, failed: 0, skipped: 0 } },
    },
  }
}

async function mount(source, { keepStatus = false } = {}) {
  if (!keepStatus) vi.mocked(getIngestStatus).mockResolvedValue(status(source))
  vi.mocked(getIngestDocuments).mockResolvedValue({ items: [], total: 0, computing: false })
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: AdminIngestionView }],
  })
  router.push('/')
  await router.isReady()
  host = document.createElement('div')
  document.body.appendChild(host)
  app = createApp(AdminIngestionView)
  app.use(router).use(i18n)
  app.mount(host)
  await new Promise((r) => setTimeout(r))
  await nextTick()
}

const meta = () => host.querySelector('.run-meta')?.textContent.trim()

describe('AdminIngestionView run source', () => {
  beforeEach(() => {
    localStorage.clear()
    setLocale('en')
  })
  afterEach(() => {
    app.unmount()
    host.remove()
    localStorage.clear()
    setLocale('en')
  })

  it('shows the raw source in English, as before', async () => {
    await mount('cron')
    expect(meta()).toMatch(/^cron · started /)
  })

  it('translates a known source in Turkish and follows a language switch', async () => {
    await mount('manual')
    expect(meta()).toMatch(/^manual · started /)
    setLocale('tr')
    await nextTick()
    expect(meta()).toMatch(/^elle · başlangıç: /)
  })

  it('shows an unknown source as received', async () => {
    setLocale('tr')
    await mount('future-runner')
    expect(meta()).toMatch(/^future-runner · başlangıç: /)
  })
})

describe('AdminIngestionView tabs', () => {
  afterEach(() => {
    app.unmount()
    host.remove()
  })

  it('keeps the indexed reports on their own tab', async () => {
    await mount('cron')
    const tabs = [...host.querySelectorAll('.tab-btn')]
    expect(tabs.map((b) => b.textContent.trim())).toEqual(['Ingestion', 'Reports', 'Users'])
    expect(host.querySelector('.run-meta')).not.toBeNull()
    expect(host.querySelector('.doc-search')).toBeNull()

    tabs[1].click()
    await nextTick()
    expect(host.querySelector('.doc-search')).not.toBeNull()
    expect(host.querySelector('.run-meta')).toBeNull()
    expect(tabs[1].getAttribute('aria-current')).toBe('true')
  })
})

describe('AdminIngestionView status', () => {
  afterEach(() => {
    app.unmount()
    host.remove()
  })

  it('shows the last ingest as day.month.year and time, not a raw timestamp', async () => {
    vi.mocked(getIngestStatus).mockResolvedValue({
      ...status('cron'),
      last_ingest: '2026-11-18T22:41:07+00:00',
    })
    await mount('cron', { keepStatus: true })
    const dd = host.querySelector('.grid dd')
    expect(dd.textContent.trim()).toMatch(/^\d{2}\.\d{2}\.2026 \d{2}:\d{2}$/)
    expect(dd.classList.contains('num')).toBe(true)
  })
})
