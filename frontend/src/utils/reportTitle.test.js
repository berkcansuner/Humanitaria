import { describe, it, expect } from 'vitest'
import { splitReportTitle, formatPeriod } from './reportTitle.js'

describe('splitReportTitle', () => {
  it('splits a situation report title (no type prefix)', () => {
    expect(splitReportTitle('Sudan · Food and Nutrition · 2026-05-15 – 2026-11-15')).toEqual({
      heading: 'Sudan',
      sector: 'Food and Nutrition',
      period: '2026-05-15 – 2026-11-15',
    })
  })

  it('drops the type prefix so the country leads', () => {
    expect(
      splitReportTitle(
        'Indicator Monitoring Report — Afghanistan · All sectors · 2025-11-15 – 2026-11-15',
      ),
    ).toEqual({ heading: 'Afghanistan', sector: 'All sectors', period: '2025-11-15 – 2026-11-15' })
  })

  it('keeps an open-ended period as written', () => {
    expect(splitReportTitle('Haiti · Health · … – 2026-11-01').period).toBe('… – 2026-11-01')
  })

  it('returns an unexpected title whole', () => {
    expect(splitReportTitle('Custom title')).toEqual({
      heading: 'Custom title',
      sector: '',
      period: '',
    })
    expect(splitReportTitle(null)).toEqual({ heading: '', sector: '', period: '' })
  })
})

describe('formatPeriod', () => {
  it('writes ISO dates as day.month.year with a plain hyphen', () => {
    expect(formatPeriod('2025-11-17 – 2026-11-17')).toBe('17.11.2025 - 17.11.2026')
  })

  it('leaves other text alone', () => {
    expect(formatPeriod('')).toBe('')
    expect(formatPeriod(null)).toBe('')
    expect(formatPeriod('last 12 months')).toBe('last 12 months')
  })
})
