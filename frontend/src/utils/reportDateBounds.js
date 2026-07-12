/**
 * Selectable date bounds for the M&E report form. Prod retains ~1 year of data
 * (RETENTION_DAYS=365), so the form's date pickers are clamped to [one year ago,
 * today] — a user can't pick a window with no indexed reports, or a future date.
 * UTC methods keep the ISO output deterministic regardless of the runner's timezone.
 */
function _isoDay(d) {
  return d.toISOString().slice(0, 10)
}

/** Earliest selectable report date. Standart raporlar 1 yıl geriye; teknik izleme
 * raporu trend için daha uzun geçmiş ister (5 yıl). */
export function minReportDate(today = new Date(), reportType = 'situation') {
  const d = new Date(today.getTime())
  const years = reportType === 'technical_monitoring' ? 5 : 1
  d.setUTCFullYear(d.getUTCFullYear() - years)
  return _isoDay(d)
}

/** Latest selectable report date: `today` — no future dates (ISO YYYY-MM-DD). */
export function maxReportDate(today = new Date()) {
  return _isoDay(today)
}
