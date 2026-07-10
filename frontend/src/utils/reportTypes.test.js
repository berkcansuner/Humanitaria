import { describe, it, expect } from 'vitest'
import { REPORT_TYPES, reportTypeBadge } from './reportTypes.js'

describe('reportTypes', () => {
  it('lists exactly the three backend report types', () => {
    expect(REPORT_TYPES.map((t) => t.value)).toEqual([
      'situation',
      'indicator_monitoring',
      'needs_assessment',
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
})
