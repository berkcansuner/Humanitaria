import { describe, it, expect } from 'vitest'
import { groupSeries, newerInSeries, olderInSeries, seriesKey } from './reportSeries.js'

// Rows as /reports/list returns them: newest created first.
function row(id, over = {}) {
  return {
    id,
    report_type: 'situation',
    country: 'Afghanistan',
    theme: 'Health',
    language: 'en',
    date_from: '2026-01-01',
    date_to: '2026-03-31',
    created_at: '2026-04-01T00:00:00Z',
    previous_report_id: null,
    ...over,
  }
}

describe('seriesKey', () => {
  it('is type + country + sector + language', () => {
    expect(seriesKey(row('a'))).toBe(seriesKey(row('b', { date_from: '2025-01-01' })))
    for (const [field, value] of [
      ['report_type', 'needs_assessment'],
      ['country', 'Sudan'],
      ['theme', 'Education'],
      ['language', 'tr'],
    ]) {
      expect(seriesKey(row('b', { [field]: value }))).not.toBe(seriesKey(row('a')))
    }
  })

  it('treats a missing type as situation and a missing sector as all sectors', () => {
    expect(seriesKey(row('a', { report_type: null }))).toBe(seriesKey(row('b')))
    expect(seriesKey(row('a', { theme: null }))).toBe(seriesKey(row('b', { theme: undefined })))
  })
})

describe('groupSeries', () => {
  it('keeps a lone report as a single entry', () => {
    expect(groupSeries([row('a')])).toEqual([{ kind: 'single', report: row('a') }])
  })

  it('folds same-key reports into one series, newest period first', () => {
    const q1 = row('q1', { date_from: '2026-01-01', date_to: '2026-03-31' })
    const q3 = row('q3', { date_from: '2026-07-01', date_to: '2026-09-30' })
    const q2 = row('q2', { date_from: '2026-04-01', date_to: '2026-06-30' })
    const [entry, ...rest] = groupSeries([q1, q3, q2])
    expect(rest).toEqual([])
    expect(entry.kind).toBe('series')
    expect(entry.key).toBe(seriesKey(q1))
    expect(entry.reports.map((r) => r.id)).toEqual(['q3', 'q2', 'q1'])
    expect(entry.latest.id).toBe('q3')
  })

  it('places a series where its most recently created report sits', () => {
    const sudan = row('s', { country: 'Sudan' })
    const afgNew = row('a2', { date_from: '2026-04-01' })
    const yemen = row('y', { country: 'Yemen' })
    const afgOld = row('a1')
    const out = groupSeries([sudan, afgNew, yemen, afgOld])
    expect(out.map((e) => (e.kind === 'series' ? e.key : e.report.id))).toEqual([
      's',
      seriesKey(afgNew),
      'y',
    ])
  })

  it('orders same-period reports by creation, newest first', () => {
    const later = row('later', { created_at: '2026-05-02T00:00:00Z' })
    const earlier = row('earlier', { created_at: '2026-05-01T00:00:00Z' })
    expect(groupSeries([earlier, later])[0].reports.map((r) => r.id)).toEqual(['later', 'earlier'])
  })

  it('sorts open-ended periods by whichever date is set', () => {
    const noEnd = row('noEnd', { date_from: '2026-07-01', date_to: null })
    const closed = row('closed', { date_from: '2026-01-01', date_to: '2026-03-31' })
    expect(groupSeries([closed, noEnd])[0].reports.map((r) => r.id)).toEqual(['noEnd', 'closed'])
  })

  it('returns an empty list for no reports', () => {
    expect(groupSeries([])).toEqual([])
    expect(groupSeries(undefined)).toEqual([])
  })
})

describe('newerInSeries', () => {
  const q1 = row('q1', { date_from: '2026-01-01', date_to: '2026-03-31' })
  const q2 = row('q2', { date_from: '2026-04-01', date_to: '2026-06-30' })
  const q3 = row('q3', { date_from: '2026-07-01', date_to: '2026-09-30' })
  const other = row('o', { country: 'Sudan' })

  it('is the next period after the given report in its series', () => {
    expect(newerInSeries([q3, other, q1, q2], 'q1').id).toBe('q2')
    expect(newerInSeries([q3, other, q1, q2], 'q2').id).toBe('q3')
  })

  it('is null for the latest period, a lone report or an unknown id', () => {
    expect(newerInSeries([q3, q1, q2], 'q3')).toBeNull()
    expect(newerInSeries([q3, other], 'o')).toBeNull()
    expect(newerInSeries([q3], 'missing')).toBeNull()
    expect(newerInSeries(undefined, 'q1')).toBeNull()
  })
})

describe('olderInSeries', () => {
  const q1 = row('q1', { date_from: '2026-01-01', date_to: '2026-03-31' })
  const q2 = row('q2', { date_from: '2026-04-01', date_to: '2026-06-30' })
  const q3 = row('q3', { date_from: '2026-07-01', date_to: '2026-09-30' })

  it('is the period before the given report in its series', () => {
    expect(olderInSeries([q3, q1, q2], 'q3').id).toBe('q2')
    expect(olderInSeries([q3, q1, q2], 'q2').id).toBe('q1')
  })

  it('is null for the first period, a lone report or an unknown id', () => {
    expect(olderInSeries([q3, q1, q2], 'q1')).toBeNull()
    expect(olderInSeries([q3], 'q3')).toBeNull()
    expect(olderInSeries([q3, q1], 'missing')).toBeNull()
  })
})
