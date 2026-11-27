import { describe, it, expect } from 'vitest'
import { localIsoDay, minReportDate, maxReportDate } from './reportDateBounds.js'

// Dates are built from local components: the bounds follow the reader's calendar
// day, not UTC (critique 3: in Türkiye, UTC+3, the form said "yesterday" until 03:00).
describe('reportDateBounds', () => {
  it('localIsoDay is the local calendar day as YYYY-MM-DD', () => {
    expect(localIsoDay(new Date(2026, 10, 16, 0, 30))).toBe('2026-11-16')
    expect(localIsoDay(new Date(2026, 0, 5, 23, 59))).toBe('2026-01-05')
  })

  it('maxReportDate is the local day, also just after midnight', () => {
    expect(maxReportDate(new Date(2026, 10, 16, 0, 30))).toBe('2026-11-16')
    expect(maxReportDate(new Date(2026, 6, 11, 9))).toBe('2026-07-11')
  })

  it('minReportDate is exactly one year before the given day', () => {
    expect(minReportDate(new Date(2026, 6, 11, 9))).toBe('2025-07-11')
    expect(minReportDate(new Date(2026, 10, 16, 0, 30))).toBe('2025-11-16')
  })

  it('handles a leap-day origin without crashing', () => {
    // 2028-02-29 minus one year → 2027-03-01 (JS Date normalises the missing Feb 29).
    expect(minReportDate(new Date(2028, 1, 29, 12))).toBe('2027-03-01')
  })
})
