import { describe, it, expect } from 'vitest'
import { validateAuth } from './authValidation.js'

const ok = { isSignup: false, name: '', email: 'a@b.co', password: 'longenough' }

describe('validateAuth', () => {
  it('accepts a complete login', () => {
    expect(validateAuth(ok)).toBeNull()
  })
  it('asks for a name only when signing up', () => {
    expect(validateAuth({ ...ok, isSignup: false, name: '' })).toBeNull()
    expect(validateAuth({ ...ok, isSignup: true, name: '  ' })).toBe('auth.validation.name')
  })
  it('rejects an empty or malformed email', () => {
    expect(validateAuth({ ...ok, email: ' ' })).toBe('auth.validation.email')
    expect(validateAuth({ ...ok, email: 'nope' })).toBe('auth.validation.emailInvalid')
  })
  it('rejects an empty password', () => {
    expect(validateAuth({ ...ok, password: '' })).toBe('auth.validation.password')
  })
  it('rejects a password under 8 characters', () => {
    expect(validateAuth({ ...ok, password: 'short' })).toBe('errors.weak_password')
  })
})
