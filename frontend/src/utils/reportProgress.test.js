import { describe, it, expect } from 'vitest'
import { reportOutline, progressStage, elapsedClock, SLOW_AFTER_S } from './reportProgress.js'

describe('reportOutline', () => {
  it("lists each type's sections in the order its prompt asks for", () => {
    expect(reportOutline('situation')).toEqual(['executiveSummary', 'keyFindings', 'outlook'])
    expect(reportOutline('indicator_monitoring')).toEqual([
      'overview',
      'indicatorTable',
      'dataGaps',
      'recentDevelopments',
    ])
    expect(reportOutline('needs_assessment')).toEqual([
      'context',
      'priorityNeeds',
      'affectedGroups',
      'gapsConstraints',
      'recommendations',
    ])
  })

  it('reads an unknown type as a situation report', () => {
    expect(reportOutline(undefined)).toEqual(reportOutline('situation'))
  })
})

describe('progressStage', () => {
  it('names the wait before the first word by what the pipeline does', () => {
    expect(progressStage({ elapsed: 5 })).toBe('reading')
  })

  it('says it is taking longer than usual only once the usual time has passed', () => {
    expect(progressStage({ elapsed: SLOW_AFTER_S - 1 })).toBe('reading')
    expect(progressStage({ elapsed: SLOW_AFTER_S })).toBe('slow')
  })

  it('becomes factual once the server says what it read', () => {
    expect(progressStage({ reading: { count: 12 }, elapsed: 5 })).toBe('readingCount')
    // A long wait is still said to be long; words still win over both.
    expect(progressStage({ reading: { count: 12 }, elapsed: 130 })).toBe('slow')
    expect(progressStage({ reading: { count: 12 }, started: true })).toBe('writing')
  })

  it('follows the stream once words arrive', () => {
    expect(progressStage({ started: true, elapsed: 300 })).toBe('writing')
  })
})

describe('elapsedClock', () => {
  it('writes minutes and two-digit seconds', () => {
    expect(elapsedClock(0)).toBe('0:00')
    expect(elapsedClock(7)).toBe('0:07')
    expect(elapsedClock(92)).toBe('1:32')
    expect(elapsedClock(600)).toBe('10:00')
  })
})
