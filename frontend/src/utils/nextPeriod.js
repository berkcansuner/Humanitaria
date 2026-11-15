/**
 * The period a report series' next report should cover (docs/report-series-brief.md).
 *
 * The length carries over from the previous report: whole calendar months stay
 * whole months (a quarter → the next quarter, January → all of February), any
 * other span stays the same number of days. The suggestion stays inside what the
 * form accepts: an end after today is pulled back to today (`endClamped`, the
 * period is not finished yet), and a start before the data window is moved up to
 * it (`startClamped`). When the next period would start after today there is
 * nothing to run yet: `{ notStarted, startsOn }`. Without both dates on the
 * previous report there is no length to carry over: `null`.
 *
 * Dates are ISO YYYY-MM-DD strings handled in UTC, like reportDateBounds.js.
 */
import { minReportDate, maxReportDate } from './reportDateBounds.js'

const DAY = 24 * 60 * 60 * 1000

function parse(iso) {
  return new Date(`${iso}T00:00:00Z`)
}
function iso(d) {
  return d.toISOString().slice(0, 10)
}
function addDays(d, n) {
  return new Date(d.getTime() + n * DAY)
}
// Last day of the month `months` months after d's month (0 = d's own month).
function monthEnd(d, months = 0) {
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + months + 1, 0))
}

function isWholeMonths(from, to) {
  return from.getUTCDate() === 1 && iso(to) === iso(monthEnd(to))
}

export function nextPeriod(previous, today = new Date(), reportType) {
  if (!previous || !previous.date_from || !previous.date_to) return null
  const from = parse(previous.date_from)
  const to = parse(previous.date_to)

  const nextFrom = addDays(to, 1)
  let nextTo
  if (isWholeMonths(from, to)) {
    const months =
      (to.getUTCFullYear() - from.getUTCFullYear()) * 12 + (to.getUTCMonth() - from.getUTCMonth())
    nextTo = monthEnd(nextFrom, months)
  } else {
    nextTo = addDays(nextFrom, Math.round((to - from) / DAY))
  }

  const max = maxReportDate(today)
  if (iso(nextFrom) > max) return { notStarted: true, startsOn: iso(nextFrom) }
  const min = minReportDate(today, reportType || previous.report_type || 'situation')

  const startClamped = iso(nextFrom) < min
  // Entirely before the window: keep the length, starting at the window.
  if (iso(nextTo) < min) nextTo = addDays(parse(min), Math.round((nextTo - nextFrom) / DAY))
  const endClamped = iso(nextTo) > max
  return {
    date_from: startClamped ? min : iso(nextFrom),
    date_to: endClamped ? max : iso(nextTo),
    endClamped,
    startClamped,
  }
}
