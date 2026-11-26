/**
 * M&E report type metadata shared between the generation form, the saved list
 * and the viewer. Values must match the backend's report_type Literal
 * (api/routes/reports.py ReportRequest.report_type). Names are interface text,
 * looked up from the code when rendered (`reports.types.*`), so they follow a
 * language switch; `t` defaults to the app's i18n.
 */
import { t as appT } from '../i18n/index.js'

export const REPORT_TYPES = [
  { value: 'situation' },
  { value: 'indicator_monitoring' },
  { value: 'needs_assessment' },
]

const KNOWN = new Set(REPORT_TYPES.map((r) => r.value))

/** The full type name ("Situation Report"); an unknown type reads as a situation report. */
export function reportTypeLabel(type, t = appT) {
  return t(`reports.types.${KNOWN.has(type) ? type : 'situation'}`)
}

// The form's sectors are ReliefWeb theme names (api/routes/reports.py THEMES); the
// value sent and stored stays the theme name, the interface shows its translation.
const SECTOR_KEYS = {
  Agriculture: 'agriculture',
  'Camp Coordination and Camp Management': 'campManagement',
  'Climate Change and Environment': 'climate',
  Contributions: 'contributions',
  Coordination: 'coordination',
  'Disaster Management': 'disasterManagement',
  Education: 'education',
  'Food and Nutrition': 'foodNutrition',
  Gender: 'gender',
  Health: 'health',
  'HIV/Aids': 'hivAids',
  'Humanitarian Financing': 'humanitarianFinancing',
  'Logistics and Telecommunications': 'logistics',
  'Mine Action': 'mineAction',
  'Peacekeeping and Peacebuilding': 'peace',
  'Protection and Human Rights': 'protection',
  'Recovery and Reconstruction': 'recovery',
  'Safety and Security': 'safety',
  'Shelter and Non-Food Items': 'shelter',
  'Water Sanitation Hygiene': 'wash',
}

/** A sector's name in the interface language; no sector reads "All sectors", and a
 * theme the interface does not know is shown as it is. */
export function sectorLabel(theme, t = appT) {
  if (!theme) return t('reports.form.allSectors')
  const key = SECTOR_KEYS[theme]
  return key ? t(`reports.sectors.${key}`) : theme
}
