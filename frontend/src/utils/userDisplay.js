/** Avatar initials for a user object ({ name, email }) — shared by the sidebar
 * footer and the header user menu. */
export function userInitials(user) {
  const n = user?.name?.trim()
  if (n) {
    const p = n.split(/\s+/)
    return ((p[0]?.[0] || '') + (p[1]?.[0] || '')).toUpperCase() || n[0].toUpperCase()
  }
  const e = user?.email
  return e ? e[0].toUpperCase() : '?'
}
