/**
 * Whether a retrieved source should be shown to the user as a citable source.
 *
 * Shared by SourceList (what renders in the panel) and renderMarkdown (which
 * citation [n] markers become clickable chips) so the two never disagree — a
 * chip is only clickable when its source is actually displayed.
 *
 * Drops sources with no url (nothing to link to) and country-metadata entries
 * whose title is just the country name (index artefacts, not real reports).
 */
export function isValidSource(src) {
  if (!src || !src.url) return false
  if (src.doctype === 'country' && src.title === src.country) return false
  return true
}

/**
 * Distinct publishers for the collapsed sources line ("WFP, OCHA, UNICEF +2"),
 * in first-seen order. Sources without a publisher are skipped.
 */
export function summarizePublishers(sources, max = 3) {
  const seen = []
  for (const src of sources || []) {
    const name = src && src.source
    if (name && !seen.includes(name)) seen.push(name)
  }
  const shown = seen.slice(0, max).join(', ')
  return seen.length > max ? `${shown} +${seen.length - max}` : shown
}

/** The YYYY-MM-DD part of an ISO date for the ledger's Date column; '' otherwise. */
export function ledgerDate(iso) {
  const m = /^(\d{4}-\d{2}-\d{2})/.exec(iso || '')
  return m ? m[1] : ''
}

/**
 * Reveal the source a citation chip points to, inside `container` (one chat
 * message or the report viewer): open the collapsed sources ledger, mark that
 * row as the single active one, scroll it into view and pulse it briefly.
 * Returns false (and changes nothing) when that source is not shown.
 */
export function revealSource(container, id) {
  const item = container?.querySelector(`.source-item[data-srcid="${id}"]`)
  if (!item) return false
  const ledger = item.closest('details')
  if (ledger) ledger.open = true
  container.querySelectorAll('.source-item.active').forEach((el) => el.classList.remove('active'))
  item.classList.add('active')
  item.scrollIntoView({ behavior: 'smooth', block: 'center' })
  item.classList.add('flash')
  setTimeout(() => item.classList.remove('flash'), 1500)
  return true
}
