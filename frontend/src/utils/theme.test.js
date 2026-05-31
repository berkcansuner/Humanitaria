import { describe, it, expect, beforeEach, vi } from 'vitest'
import { getInitialTheme, applyTheme, setTheme } from './theme.js'

describe('theme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    // Default matchMedia: not dark, unless a test overrides it.
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: false }))
  })

  describe('getInitialTheme', () => {
    it('prefers a stored theme over the system preference', () => {
      localStorage.setItem('theme', 'dark')
      vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: false }))
      expect(getInitialTheme()).toBe('dark')
    })

    it('falls back to dark when the system prefers dark and nothing is stored', () => {
      vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }))
      expect(getInitialTheme()).toBe('dark')
    })

    it('falls back to light when the system prefers light and nothing is stored', () => {
      vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: false }))
      expect(getInitialTheme()).toBe('light')
    })

    it('ignores an invalid stored value and uses the system preference', () => {
      localStorage.setItem('theme', 'banana')
      vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }))
      expect(getInitialTheme()).toBe('dark')
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
  })
})
