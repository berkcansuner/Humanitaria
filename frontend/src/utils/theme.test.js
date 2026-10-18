import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { getInitialTheme, applyTheme, setTheme } from './theme.js'

function blockedStorage() {
  const blocked = () => {
    throw new DOMException('blocked', 'SecurityError')
  }
  return { getItem: blocked, setItem: blocked, clear: blocked }
}

describe('theme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    // Default matchMedia: not dark, unless a test overrides it.
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: false }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('getInitialTheme', () => {
    it('prefers a stored theme', () => {
      localStorage.setItem('theme', 'dark')
      expect(getInitialTheme()).toBe('dark')
    })

    it('defaults to light when nothing is stored (ignores OS preference)', () => {
      vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }))
      expect(getInitialTheme()).toBe('light')
    })

    it('ignores an invalid stored value and defaults to light', () => {
      localStorage.setItem('theme', 'banana')
      vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }))
      expect(getInitialTheme()).toBe('light')
    })

    it('defaults to light instead of throwing when storage is blocked', () => {
      vi.stubGlobal('localStorage', blockedStorage())
      expect(getInitialTheme()).toBe('light')
    })
  })

  describe('applyTheme', () => {
    it('sets data-theme on the document element', () => {
      applyTheme('dark')
      expect(document.documentElement.dataset.theme).toBe('dark')
    })
  })

  describe('setTheme', () => {
    it('persists the theme and applies it', () => {
      setTheme('dark')
      expect(localStorage.getItem('theme')).toBe('dark')
      expect(document.documentElement.dataset.theme).toBe('dark')
    })

    it('still applies the theme when storage is blocked', () => {
      vi.stubGlobal('localStorage', blockedStorage())
      setTheme('dark')
      expect(document.documentElement.dataset.theme).toBe('dark')
    })
  })
})
