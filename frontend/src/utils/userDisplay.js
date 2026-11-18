/** Avatar initials from a name and/or email. `locale` sets the case mapping, so a Turkish
 * "ismail" gives "İ" (dotted capital), not "I". */
export function initials(name, email, locale = 'en') {
  const upper = (s) => s.toLocaleUpperCase(locale === 'tr' ? 'tr-TR' : 'en-US')
  const n = name?.trim()
  if (n) {
    const p = n.split(/\s+/)
    return upper((p[0]?.[0] || '') + (p[1]?.[0] || '')) || upper(n[0])
  }
  return email ? upper(email[0]) : '?'
}

/** Avatar initials for a user object ({ name, email }) — shared by the sidebar
 * footer and the header user menu. */
export function userInitials(user, locale = 'en') {
  return initials(user?.name, user?.email, locale)
}
