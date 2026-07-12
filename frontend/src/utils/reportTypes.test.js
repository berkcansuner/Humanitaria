import { describe, it, expect } from 'vitest'
import { REPORT_TYPES, reportTypeBadge } from './reportTypes.js'

describe('reportTypes', () => {
  it('lists exactly the four backend report types', () => {
    expect(REPORT_TYPES.map((t) => t.value)).toEqual([
      'situation',
      'indicator_monitoring',
      'needs_assessment',
      'technical_monitoring',
    ])
  })

  it('returns a short badge for non-situation types', () => {
    expect(reportTypeBadge('indicator_monitoring')).toBe('Indicator Monitoring')
    expect(reportTypeBadge('needs_assessment')).toBe('Needs Assessment')
  })

  it('returns null for situation and unknown types (no badge)', () => {
    expect(reportTypeBadge('situation')).toBeNull()
    expect(reportTypeBadge(undefined)).toBeNull()
    expect(reportTypeBadge('')).toBeNull()
  })

  it('includes the technical_monitoring type', () => {
    const values = REPORT_TYPES.map((t) => t.value)
    expect(values).toContain('technical_monitoring')
  })

  it('has a badge for technical_monitoring', () => {
    expect(reportTypeBadge('technical_monitoring')).toBe('Technical Monitoring')
  })
})
