import { describe, it, expect, afterEach } from 'vitest'
import { REPORT_TYPES, reportTypeBadge, reportTypeLabel, sectorLabel } from './reportTypes.js'
import { setLocale } from '../i18n/locale.js'
import en from '../locales/en.json'

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

  it('names each type in full', () => {
    expect(reportTypeLabel('situation')).toBe('Situation Report')
    expect(reportTypeLabel('technical_monitoring')).toBe('Technical Monitoring Report')
    expect(reportTypeLabel(undefined)).toBe('Situation Report')
  })

  describe('in Turkish', () => {
    afterEach(() => {
      setLocale('en')
      localStorage.clear()
    })

    it('names types and sectors in the interface language, looked up when called', () => {
      setLocale('tr')
      expect(reportTypeLabel('indicator_monitoring')).toBe('Gösterge izleme raporu')
      expect(reportTypeBadge('needs_assessment')).toBe('İhtiyaç değerlendirmesi')
      expect(sectorLabel('Water Sanitation Hygiene')).toBe('Su, sanitasyon ve hijyen')
      expect(sectorLabel(null)).toBe('Tüm sektörler')
    })
  })
})

describe('sectorLabel', () => {
  it('keeps the ReliefWeb theme names in English', () => {
    expect(sectorLabel('Food and Nutrition')).toBe('Food and Nutrition')
    expect(sectorLabel('')).toBe('All sectors')
  })

  it('shows a theme it does not know as it is', () => {
    expect(sectorLabel('Some New Theme')).toBe('Some New Theme')
  })

  it('has an English name equal to the theme for every sector key', () => {
    for (const name of Object.values(en.reports.sectors)) expect(sectorLabel(name)).toBe(name)
    expect(Object.keys(en.reports.sectors)).toHaveLength(20)
  })
})
