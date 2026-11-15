/**
 * Report series for the saved list (docs/report-series-brief.md).
 *
 * A series is implicit: reports with the same type + country + sector + language.
 * There is no "create series" step, so two one-off reports with the same settings
 * fold together too, which is what an M&E officer re-running a report expects.
 */

export function seriesKey(r) {
  return [r.report_type || 'situation', r.country || '', r.theme || '', r.language || ''].join(
    '\u0000',
  )
}

// Newest period first: the end date when set, otherwise the start date; equal
// periods fall back to creation time.
function periodDesc(a, b) {
  const pa = a.date_to || a.date_from || ''
  const pb = b.date_to || b.date_from || ''
  if (pa !== pb) return pa < pb ? 1 : -1
  const ca = a.created_at || ''
  const cb = b.created_at || ''
  return ca === cb ? 0 : ca < cb ? 1 : -1
}

/**
 * Fold the saved list (newest created first, as /reports/list returns it) into
 * entries for display:
 *   { kind: 'single', report }
 *   { kind: 'series', key, reports (newest period first), latest }
 * A series takes the place of its most recently created report, so the list
 * order the user knows stays put.
 */
export function groupSeries(reports) {
  const groups = new Map()
  for (const r of reports || []) {
    const key = seriesKey(r)
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(r)
  }
  const out = []
  for (const [key, members] of groups) {
    if (members.length === 1) {
      out.push({ kind: 'single', report: members[0] })
    } else {
      const sorted = [...members].sort(periodDesc)
      out.push({ kind: 'series', key, reports: sorted, latest: sorted[0] })
    }
  }
  return out
}

/**
 * The report that comes right after `id` in its series (the next newer period),
 * or null when `id` is the series' latest, a lone report, or unknown. The header
 * of an older period links forward to it ("Continued by …").
 */
export function newerInSeries(reports, id) {
  for (const entry of groupSeries(reports)) {
    if (entry.kind !== 'series') continue
    const i = entry.reports.findIndex((r) => r.id === id)
    if (i >= 0) return i > 0 ? entry.reports[i - 1] : null
  }
  return null
}

/**
 * The report right before `id` in its series (the previous period), or null when
 * `id` is the series' first, a lone report, or unknown. A series is implicit, so
 * a report can have an earlier period it was never compared with (it was made as
 * a one-off); the header says so instead of leaving the gap unexplained.
 */
export function olderInSeries(reports, id) {
  for (const entry of groupSeries(reports)) {
    if (entry.kind !== 'series') continue
    const i = entry.reports.findIndex((r) => r.id === id)
    if (i >= 0) return i < entry.reports.length - 1 ? entry.reports[i + 1] : null
  }
  return null
}
