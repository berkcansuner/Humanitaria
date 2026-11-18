const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+$/

/**
 * Client-side check of the sign-in / sign-up form. Returns the message key of the
 * first problem, or null. Done here (not by the browser) so the text follows the
 * interface language rather than the browser's.
 */
export function validateAuth({ isSignup, name, email, password }) {
  if (isSignup && !name.trim()) return 'auth.validation.name'
  const mail = email.trim()
  if (!mail) return 'auth.validation.email'
  if (!EMAIL_SHAPE.test(mail)) return 'auth.validation.emailInvalid'
  if (!password) return 'auth.validation.password'
  if (password.length < 8) return 'errors.weak_password'
  return null
}
