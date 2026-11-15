import { describe, it, expect } from 'vitest'
import { nextPeriod } from './nextPeriod.js'

const TODAY = new Date('2026-11-15T12:00:00Z')

function prev(date_from, date_to, report_type = 'situation') {
  return { date_from, date_to, report_type }
}

describe('nextPeriod', () => {
  it('carries a whole quarter over to the next quarter', () => {
    expect(nextPeriod(prev('2026-04-01', '2026-06-30'), TODAY)).toEqual({
      date_from: '2026-07-01',
      date_to: '2026-09-30',
      endClamped: false,
      startClamped: false,
    })
  })

  it('carries a whole month over to the next month, whatever its length', () => {
    expect(nextPeriod(prev('2026-01-01', '2026-01-31'), TODAY)).toMatchObject({
      date_from: '2026-02-01',
      date_to: '2026-02-28',
    })
  })

  it('carries whole months across a year end', () => {
    expect(
      nextPeriod(prev('2025-11-01', '2025-12-31'), new Date('2026-06-01T00:00:00Z')),
    ).toMatchObject({ date_from: '2026-01-01', date_to: '2026-02-28' })
  })

  it('carries an arbitrary span over as the same number of days', () => {
    // 2026-08-10 .. 2026-08-23 is 14 days; the next 14 start the day after.
    expect(nextPeriod(prev('2026-08-10', '2026-08-23'), TODAY)).toMatchObject({
      date_from: '2026-08-24',
      date_to: '2026-09-06',
    })
  })

  it('ends a period that is not finished yet today', () => {
    expect(nextPeriod(prev('2026-07-01', '2026-09-30'), TODAY)).toEqual({
      date_from: '2026-10-01',
      date_to: '2026-11-15',
      endClamped: true,
      startClamped: false,
    })
  })

  it('says when the next period has not started yet', () => {
    // The form's default period ends today: the next one starts tomorrow.
    expect(nextPeriod(prev('2026-08-15', '2026-11-15'), TODAY)).toEqual({
      notStarted: true,
      startsOn: '2026-11-16',
    })
  })

  it('moves a start older than the 12-month data window up to the window', () => {
    expect(nextPeriod(prev('2025-07-01', '2025-09-30'), TODAY)).toEqual({
      date_from: '2025-11-15',
      date_to: '2025-12-31',
      endClamped: false,
      startClamped: true,
    })
  })

  it('keeps the length when the whole next period is older than the window', () => {
    // Next would be 2025-04-01 .. 2025-06-30 (91 days), all before 2025-11-15.
    expect(nextPeriod(prev('2025-01-01', '2025-03-31'), TODAY)).toEqual({
      date_from: '2025-11-15',
      date_to: '2026-02-13',
      endClamped: false,
      startClamped: true,
    })
  })

  it('uses the 5-year window for technical monitoring reports', () => {
    expect(
      nextPeriod(prev('2025-07-01', '2025-09-30', 'technical_monitoring'), TODAY),
    ).toMatchObject({ date_from: '2025-10-01', startClamped: false })
  })

  it('cannot suggest a period without both dates', () => {
    expect(nextPeriod(prev(null, '2026-06-30'), TODAY)).toBeNull()
    expect(nextPeriod(prev('2026-04-01', null), TODAY)).toBeNull()
    expect(nextPeriod(null, TODAY)).toBeNull()
  })
})
