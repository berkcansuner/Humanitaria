import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  normalizeLocale,
  initialLocale,
  setLocale,
  hasExplicitChoice,
  onLocaleChange,
} from './locale.js'

describe('locale', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.lang = ''
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('normalizes supported values and rejects the rest', () => {
    expect(normalizeLocale('TR')).toBe('tr')
    expect(normalizeLocale(' en ')).toBe('en')
    expect(normalizeLocale('de')).toBeNull()
    expect(normalizeLocale(undefined)).toBeNull()
    expect(normalizeLocale(5)).toBeNull()
  })

  it('initialLocale reads the stored explicit choice, else en', () => {
    expect(initialLocale()).toBe('en')
    localStorage.setItem('lang', 'tr')
    expect(initialLocale()).toBe('tr')
    localStorage.setItem('lang', 'xx')
    expect(initialLocale()).toBe('en')
  })

  it('initialLocale never throws when storage does', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied')
    })
    expect(initialLocale()).toBe('en')
    expect(hasExplicitChoice()).toBe(false)
  })

  it('setLocale sets html lang and stores an explicit choice', () => {
    setLocale('tr')
    expect(document.documentElement.lang).toBe('tr')
    expect(localStorage.getItem('lang')).toBe('tr')
    expect(hasExplicitChoice()).toBe(true)
  })

  it('setLocale with explicit:false does not store', () => {
    setLocale('tr', { explicit: false })
    expect(document.documentElement.lang).toBe('tr')
    expect(localStorage.getItem('lang')).toBeNull()
    expect(hasExplicitChoice()).toBe(false)
  })

  it('setLocale ignores unsupported values and survives a throwing setItem', () => {
    setLocale('en')
    setLocale('de')
    expect(document.documentElement.lang).toBe('en')
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('denied')
    })
    expect(() => setLocale('tr')).not.toThrow()
    expect(document.documentElement.lang).toBe('tr')
  })

  it('notifies listeners until unsubscribed', () => {
    const cb = vi.fn()
    const off = onLocaleChange(cb)
    setLocale('tr')
    expect(cb).toHaveBeenCalledWith('tr')
    off()
    setLocale('en')
    expect(cb).toHaveBeenCalledTimes(1)
  })
})
