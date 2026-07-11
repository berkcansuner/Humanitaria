/**
 * Selectable date bounds for the M&E report form. Prod retains ~1 year of data
 * (RETENTION_DAYS=365), so the form's date pickers are clamped to [one year ago,
 * today] — a user can't pick a window with no indexed reports, or a future date.
 * UTC methods keep the ISO output deterministic regardless of the runner's timezone.
 */
function _isoDay(d) {
  return d.toISOString().slice(0, 10)
}

/** Earliest selectable report date: one year before `today` (ISO YYYY-MM-DD). */
export function minReportDate(today = new Date()) {
  const d = new Date(today.getTime())
  d.setUTCFullYear(d.getUTCFullYear() - 1)
  return _isoDay(d)
}

/** Latest selectable report date: `today` — no future dates (ISO YYYY-MM-DD). */
export function maxReportDate(today = new Date()) {
  return _isoDay(today)
}
