import { describe, it, expect } from 'vitest'
import { initials, userInitials } from './userDisplay.js'

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

describe('initials', () => {
  it('uppercases Turkish i as dotted İ', () => {
    expect(initials('ismail yılmaz', '', 'tr')).toBe('İY')
  })
  it('uppercases i as I in English', () => {
    expect(initials('ismail', '', 'en')).toBe('I')
  })
  it('defaults to English and falls back to the email, then ?', () => {
    expect(initials('', 'ida@example.com')).toBe('I')
    expect(initials('', 'ida@example.com', 'tr')).toBe('İ')
    expect(initials('', '')).toBe('?')
  })
  it('userInitials passes the locale through', () => {
    expect(userInitials({ name: 'ilke' }, 'tr')).toBe('İ')
  })
})
