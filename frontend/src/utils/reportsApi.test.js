import { describe, it, expect, beforeEach, vi } from 'vitest'
import { getReportOptions, listReports, getReport, deleteReport } from './reportsApi.js'

vi.mock('./authStore.js', () => ({ handleSessionExpired: vi.fn() }))

describe('reports api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('getReportOptions GETs /reports/options', async () => {
    const data = { countries: ['Sudan'], themes: ['Health'] }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(data) }),
    )
    const result = await getReportOptions()
    expect(fetch).toHaveBeenCalledWith(
      '/reports/options',
      expect.objectContaining({ method: 'GET' }),
    )
    expect(result).toEqual(data)
  })

  it('listReports GETs /reports', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ reports: [] }) }),
    )
    await listReports()
    expect(fetch).toHaveBeenCalledWith('/reports/list', expect.objectContaining({ method: 'GET' }))
  })

  it('getReport GETs the report path', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ id: 'r1' }) }),
    )
    await getReport('r1')
    expect(fetch).toHaveBeenCalledWith('/reports/r1', expect.objectContaining({ method: 'GET' }))
  })

  it('deleteReport DELETEs the report path', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ ok: true }) }),
    )
    await deleteReport('r1')
    expect(fetch).toHaveBeenCalledWith('/reports/r1', expect.objectContaining({ method: 'DELETE' }))
  })

  it('on 401 triggers session-expiry handling', async () => {
    const { handleSessionExpired } = await import('./authStore.js')
    handleSessionExpired.mockClear()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))
    await expect(listReports()).rejects.toMatchObject({ status: 401 })
    expect(handleSessionExpired).toHaveBeenCalledTimes(1)
  })
})
