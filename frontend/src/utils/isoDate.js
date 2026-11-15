/**
 * Catalog-mark dates for data views (DESIGN: "numbers that index or date something
 * are set in mono with tabular figures"): ISO order, local time, '—' when absent.
 */
function pad(n) {
  return String(n).padStart(2, '0')
}

function parse(value) {
  if (!value) return null
  const d = new Date(value)
  return isNaN(d.getTime()) ? null : d
}

/** "2026-11-15"; a bare YYYY-MM-DD string is kept as written (no time-zone shift). */
export function isoDate(value) {
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) return value
  const d = parse(value)
  if (!d) return value ? String(value) : '—'
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** "2026-11-15 16:31" in local time. */
export function isoDateTime(value) {
  const d = parse(value)
  if (!d) return '—'
  return `${isoDate(d)} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
