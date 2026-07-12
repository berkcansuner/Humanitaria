/**
 * M&E report type metadata shared between the generation form and the saved
 * list / viewer badge. Values must match the backend's report_type Literal
 * (api/routes/reports.py ReportRequest.report_type).
 */
export const REPORT_TYPES = [
  { value: 'situation', label: 'Situation Report' },
  { value: 'indicator_monitoring', label: 'Indicator Monitoring Report' },
  { value: 'needs_assessment', label: 'Needs Assessment Brief' },
  { value: 'technical_monitoring', label: 'Technical Monitoring Report' },
]

const BADGE_LABELS = {
  indicator_monitoring: 'Indicator Monitoring',
  needs_assessment: 'Needs Assessment',
  technical_monitoring: 'Technical Monitoring',
}

/** Short badge text for a report_type, or null for 'situation' (no badge shown). */
export function reportTypeBadge(type) {
  return BADGE_LABELS[type] || null
}
