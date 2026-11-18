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
    expect(reportOutline('technical_monitoring')).toEqual([
      'executiveSummary',
      'findings',
      'dataCoverage',
      'methods',
    ])
  })

  it('puts "What changed" right after the opening section of a next-period report', () => {
    expect(reportOutline('situation', { comparing: true })).toEqual([
      'executiveSummary',
      'whatChanged',
      'keyFindings',
      'outlook',
    ])
    expect(reportOutline('needs_assessment', { comparing: true }).slice(0, 2)).toEqual([
      'context',
      'whatChanged',
    ])
  })

  it('reads an unknown type as a situation report', () => {
    expect(reportOutline(undefined)).toEqual(reportOutline('situation'))
  })
})

describe('progressStage', () => {
  it('names the wait before the first word by what the pipeline does', () => {
    expect(progressStage({ type: 'situation', elapsed: 5 })).toBe('reading')
    expect(progressStage({ type: 'needs_assessment', elapsed: 5 })).toBe('reading')
    // Technical reports compute statistics in code first, then narrate them.
    expect(progressStage({ type: 'technical_monitoring', elapsed: 5 })).toBe('computing')
  })

  it('says it is taking longer than usual only once the usual time has passed', () => {
    expect(progressStage({ type: 'situation', elapsed: SLOW_AFTER_S - 1 })).toBe('reading')
    expect(progressStage({ type: 'situation', elapsed: SLOW_AFTER_S })).toBe('slow')
    expect(progressStage({ type: 'technical_monitoring', elapsed: SLOW_AFTER_S })).toBe('slow')
  })

  it('becomes factual once the server says what it read or computed', () => {
    expect(progressStage({ type: 'situation', reading: { count: 12 }, elapsed: 5 })).toBe(
      'readingCount',
    )
    expect(
      progressStage({ type: 'technical_monitoring', computed: { indicators: [] }, elapsed: 5 }),
    ).toBe('computed')
    // A long wait is still said to be long; words still win over both.
    expect(progressStage({ type: 'situation', reading: { count: 12 }, elapsed: 130 })).toBe('slow')
    expect(progressStage({ type: 'situation', reading: { count: 12 }, started: true })).toBe(
      'writing',
    )
  })

  it('follows the stream once words arrive, and the check of a next-period report', () => {
    expect(progressStage({ type: 'situation', started: true, elapsed: 300 })).toBe('writing')
    expect(progressStage({ type: 'technical_monitoring', started: true })).toBe('writingTechnical')
    expect(progressStage({ type: 'situation', started: true, checking: true })).toBe('checking')
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
