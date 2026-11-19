/**
 * Dates for data views, written day.month.year ('15.11.2026') in local time; '—' when
 * absent. (The names keep "iso" from the YYYY-MM-DD form these replaced.)
 */
function pad(n) {
  return String(n).padStart(2, '0')
}

function parse(value) {
  if (!value) return null
  const d = new Date(value)
  return isNaN(d.getTime()) ? null : d
}

/** "15.11.2026"; a bare YYYY-MM-DD string keeps its own day (no time-zone shift). */
export function isoDate(value) {
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return `${value.slice(8, 10)}.${value.slice(5, 7)}.${value.slice(0, 4)}`
  }
  const d = parse(value)
  if (!d) return value ? String(value) : '—'
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`
}

/** "15.11.2026 16:31" in local time. */
export function isoDateTime(value) {
  const d = parse(value)
  if (!d) return '—'
  return `${isoDate(d)} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
