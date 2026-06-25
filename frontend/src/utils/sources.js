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
