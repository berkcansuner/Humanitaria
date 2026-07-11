import { describe, it, expect } from 'vitest'
import { minReportDate, maxReportDate } from './reportDateBounds.js'

describe('reportDateBounds', () => {
  it('minReportDate is exactly one year before the given day (ISO YYYY-MM-DD)', () => {
    expect(minReportDate(new Date('2026-07-11T09:00:00Z'))).toBe('2025-07-11')
  })

  it('maxReportDate is the given day (no future dates), ISO YYYY-MM-DD', () => {
    expect(maxReportDate(new Date('2026-07-11T09:00:00Z'))).toBe('2026-07-11')
  })

  it('handles a leap-day origin without crashing', () => {
    // 2028-02-29 minus one year → 2027-03-01 (JS Date normalises the missing Feb 29).
    expect(minReportDate(new Date('2028-02-29T12:00:00Z'))).toBe('2027-03-01')
  })
})
