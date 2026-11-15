/**
 * Split a saved report title into the parts the viewer and the saved list show
 * separately. The backend writes titles as
 *   "[<Type label> — ]<Country> · <Sector> · <from> – <to>"
 * (rag/report_service.py report_title), so the country, which tells reports
 * apart, sat after a long type prefix and was cut off in the list.
 *
 * Returns { heading, sector, period }. A title that does not follow the format
 * comes back whole as `heading` with empty parts, so nothing is lost.
 */
export function splitReportTitle(title) {
  const text = String(title || '').trim()
  const parts = text.split(' · ')
  if (parts.length !== 3) return { heading: text, sector: '', period: '' }
  const [first, sector, period] = parts.map((p) => p.trim())
  const dash = first.lastIndexOf(' — ')
  const heading = dash >= 0 ? first.slice(dash + 3).trim() : first
  return { heading: heading || first, sector, period }
}
