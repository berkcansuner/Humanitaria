import { describe, it, expect } from 'vitest'
import { isoDate, isoDateTime } from './isoDate.js'

describe('isoDate', () => {
  it('keeps a bare YYYY-MM-DD date as written', () => {
    expect(isoDate('2026-11-15')).toBe('2026-11-15')
  })

  it('formats a timestamp in local time', () => {
    const d = new Date(2026, 10, 5, 23, 59)
    expect(isoDate(d.toISOString())).toBe('2026-11-05')
  })

  it('returns a dash for a missing value and the raw text for an unparsable one', () => {
    expect(isoDate(null)).toBe('—')
    expect(isoDate('soon')).toBe('soon')
  })
})

describe('isoDateTime', () => {
  it('formats date and time in local time, zero-padded', () => {
    const d = new Date(2026, 0, 3, 7, 4)
    expect(isoDateTime(d.toISOString())).toBe('2026-01-03 07:04')
  })

  it('returns a dash for missing or invalid input', () => {
    expect(isoDateTime(undefined)).toBe('—')
    expect(isoDateTime('nope')).toBe('—')
  })
})
