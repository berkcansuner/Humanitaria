import { describe, it, expect } from 'vitest'
import { validateAuth } from './authValidation.js'

const ok = { isSignup: false, name: '', email: 'a@b.co', password: 'longenough' }

describe('validateAuth', () => {
  it('accepts a complete login', () => {
    expect(validateAuth(ok)).toBeNull()
  })
  it('asks for a name only when signing up', () => {
    expect(validateAuth({ ...ok, isSignup: false, name: '' })).toBeNull()
    expect(validateAuth({ ...ok, isSignup: true, name: '  ' })).toEqual({
      field: 'name',
      key: 'auth.validation.name',
    })
  })
  it('rejects an empty or malformed email', () => {
    expect(validateAuth({ ...ok, email: ' ' })).toEqual({
      field: 'email',
      key: 'auth.validation.email',
    })
    expect(validateAuth({ ...ok, email: 'nope' })).toEqual({
      field: 'email',
      key: 'auth.validation.emailInvalid',
    })
  })
  it('rejects an empty password', () => {
    expect(validateAuth({ ...ok, password: '' })).toEqual({
      field: 'password',
      key: 'auth.validation.password',
    })
  })
  it('rejects a password under 8 characters', () => {
    expect(validateAuth({ ...ok, password: 'short' })).toEqual({
      field: 'password',
      key: 'errors.weak_password',
    })
  })
})
