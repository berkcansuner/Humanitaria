/**
 * Selectable date bounds for the M&E report form. Prod retains ~1 year of data
 * (RETENTION_DAYS=365), so the form's date pickers are clamped to [one year ago,
 * today] — a user can't pick a window with no indexed reports, or a future date.
 *
 * "Today" is the reader's local calendar day, not UTC: in Türkiye (UTC+3) a UTC
 * date was still yesterday until 03:00, so the form refused today's date and
 * "Run next period" said a period starting today had not started (critique 3).
 */
function pad(n) {
  return String(n).padStart(2, '0')
}

/** The local calendar day of `d` as YYYY-MM-DD. */
export function localIsoDay(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** Earliest selectable report date. Standart raporlar 1 yıl geriye; teknik izleme
 * raporu trend için daha uzun geçmiş ister (5 yıl). */
export function minReportDate(today = new Date(), reportType = 'situation') {
  const d = new Date(today.getTime())
  const years = reportType === 'technical_monitoring' ? 5 : 1
  d.setFullYear(d.getFullYear() - years)
  return localIsoDay(d)
}

/** Latest selectable report date: `today` — no future dates (ISO YYYY-MM-DD). */
export function maxReportDate(today = new Date()) {
  return localIsoDay(today)
}
