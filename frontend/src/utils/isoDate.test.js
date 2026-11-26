import { describe, it, expect } from 'vitest'
import { isoDate, isoDateTime, parseDayMonthYear } from './isoDate.js'

describe('isoDate', () => {
  it('writes a bare YYYY-MM-DD date as day.month.year, with no time-zone shift', () => {
    expect(isoDate('2026-11-15')).toBe('15.11.2026')
  })

  it('formats a timestamp in local time', () => {
    const d = new Date(2026, 10, 5, 23, 59)
    expect(isoDate(d.toISOString())).toBe('05.11.2026')
  })

  it('returns a dash for a missing value and the raw text for an unparsable one', () => {
    expect(isoDate(null)).toBe('—')
    expect(isoDate('soon')).toBe('soon')
  })
})

describe('isoDateTime', () => {
  it('formats date and time in local time, zero-padded', () => {
    const d = new Date(2026, 0, 3, 7, 4)
    expect(isoDateTime(d.toISOString())).toBe('03.01.2026 07:04')
  })

  it('returns a dash for missing or invalid input', () => {
    expect(isoDateTime(undefined)).toBe('—')
    expect(isoDateTime('nope')).toBe('—')
  })
})

describe('parseDayMonthYear', () => {
  it('reads day.month.year as YYYY-MM-DD, with or without leading zeros', () => {
    expect(parseDayMonthYear('25.08.2026')).toBe('2026-08-25')
    expect(parseDayMonthYear(' 1.9.2026 ')).toBe('2026-09-01')
  })

  it('accepts a slash or a hyphen between the parts', () => {
    expect(parseDayMonthYear('25/08/2026')).toBe('2026-08-25')
    expect(parseDayMonthYear('25-08-2026')).toBe('2026-08-25')
  })

  it('refuses a day that does not exist, a short year and other text', () => {
    expect(parseDayMonthYear('31.02.2026')).toBeNull()
    expect(parseDayMonthYear('25.13.2026')).toBeNull()
    expect(parseDayMonthYear('25.08.26')).toBeNull()
    expect(parseDayMonthYear('2026-08-25')).toBeNull()
    expect(parseDayMonthYear('')).toBeNull()
  })
})
