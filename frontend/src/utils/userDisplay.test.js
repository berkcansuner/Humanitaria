import { describe, it, expect } from 'vitest'
import { userInitials } from './userDisplay.js'

describe('userInitials', () => {
  it('uses first letters of the first two name words', () => {
    expect(userInitials({ name: 'Ada Lovelace' })).toBe('AL')
  })
  it('uses the single name initial when one word', () => {
    expect(userInitials({ name: 'Ada' })).toBe('A')
  })
  it('falls back to the email initial', () => {
    expect(userInitials({ email: 'zoe@example.com' })).toBe('Z')
  })
  it('falls back to ? when nothing is known', () => {
    expect(userInitials(null)).toBe('?')
    expect(userInitials({})).toBe('?')
  })
})
