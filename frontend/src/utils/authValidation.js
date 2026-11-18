const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+$/

/**
 * Client-side check of the sign-in / sign-up form. Returns `{ field, key }` for the
 * first problem (the input to flag and the message key), or null. Done here (not by the browser) so the text follows the
 * interface language rather than the browser's.
 */
export function validateAuth({ isSignup, name, email, password }) {
  if (isSignup && !name.trim()) return { field: 'name', key: 'auth.validation.name' }
  const mail = email.trim()
  if (!mail) return { field: 'email', key: 'auth.validation.email' }
  if (!EMAIL_SHAPE.test(mail)) return { field: 'email', key: 'auth.validation.emailInvalid' }
  if (!password) return { field: 'password', key: 'auth.validation.password' }
  if (password.length < 8) return { field: 'password', key: 'errors.weak_password' }
  return null
}
