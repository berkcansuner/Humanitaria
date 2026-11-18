import { describe, it, expect, beforeEach, vi } from 'vitest'

vi.mock('./authApi.js', () => ({
  me: vi.fn(),
  login: vi.fn(),
  signup: vi.fn(),
  logout: vi.fn(),
  updateLanguage: vi.fn(),
}))

import { me, login, signup, logout, updateLanguage } from './authApi.js'
import { setLocale } from '../i18n/locale.js'
import { auth, refresh, doLogin, doSignup, doLogout, isAuthenticated } from './authStore.js'

describe('authStore', () => {
  beforeEach(() => {
    auth.user = null
    auth.ready = false
    vi.clearAllMocks()
  })

  it('refresh populates the user from me()', async () => {
    me.mockResolvedValue({ id: '1', email: 'a@b.com' })
    await refresh()
    expect(auth.user).toEqual({ id: '1', email: 'a@b.com' })
    expect(auth.ready).toBe(true)
    expect(isAuthenticated()).toBe(true)
  })

  it('refresh leaves the user null when me() resolves null (anonymous visitor)', async () => {
    // /auth/me now answers 200 + null for anonymous visitors, so me() resolves
    // (rather than rejecting) and refresh() simply records the null user.
    me.mockResolvedValue(null)
    await refresh()
    expect(auth.user).toBeNull()
    expect(auth.ready).toBe(true)
    expect(isAuthenticated()).toBe(false)
  })

  it('refresh sets the user to null when me() rejects (network/server error)', async () => {
    me.mockRejectedValue(new Error('network down'))
    await refresh()
    expect(auth.user).toBeNull()
    expect(auth.ready).toBe(true)
    expect(isAuthenticated()).toBe(false)
  })

  it('doLogin sets the user', async () => {
    login.mockResolvedValue({ id: '2', email: 'c@d.com' })
    await doLogin('c@d.com', 'pw')
    expect(login).toHaveBeenCalledWith('c@d.com', 'pw')
    expect(auth.user).toEqual({ id: '2', email: 'c@d.com' })
  })

  it('doSignup sets the user', async () => {
    signup.mockResolvedValue({ id: '3', email: 'e@f.com' })
    await doSignup('e@f.com', 'pw', 'E')
    expect(signup).toHaveBeenCalledWith('e@f.com', 'pw', 'E')
    expect(auth.user).toEqual({ id: '3', email: 'e@f.com' })
  })

  it('doLogout clears the user even if the request resolves', async () => {
    auth.user = { id: '2' }
    logout.mockResolvedValue(null)
    await doLogout()
    expect(auth.user).toBeNull()
  })

  describe('account language sync', () => {
    beforeEach(() => {
      localStorage.clear()
      document.documentElement.lang = 'en'
      updateLanguage.mockResolvedValue({})
    })

    it('keeps an explicit device choice that differs from the account and writes it back', async () => {
      setLocale('tr')
      me.mockResolvedValue({ id: '1', ui_language: 'en' })
      await refresh()
      expect(document.documentElement.lang).toBe('tr')
      expect(updateLanguage).toHaveBeenCalledWith('tr')
    })

    it('applies the account language without storing it when the device has no choice', async () => {
      login.mockResolvedValue({ id: '1', ui_language: 'tr' })
      await doLogin('a@b.com', 'pw')
      expect(document.documentElement.lang).toBe('tr')
      expect(localStorage.getItem('lang')).toBeNull()
      expect(updateLanguage).not.toHaveBeenCalled()
    })

    it('stays English when neither the device nor the account has a language', async () => {
      signup.mockResolvedValue({ id: '1', ui_language: null })
      await doSignup('a@b.com', 'pw', 'A')
      expect(document.documentElement.lang).toBe('en')
      expect(updateLanguage).not.toHaveBeenCalled()
    })

    it('does not call updateLanguage when the device choice matches the account', async () => {
      setLocale('tr')
      me.mockResolvedValue({ id: '1', ui_language: 'tr' })
      await refresh()
      expect(updateLanguage).not.toHaveBeenCalled()
    })

    it('does not echo the account language back (non-explicit change)', async () => {
      me.mockResolvedValue({ id: '1', ui_language: 'tr' })
      await refresh()
      expect(updateLanguage).not.toHaveBeenCalled()
    })

    it('saves an explicit change made while signed in, once, across repeated logins', async () => {
      login.mockResolvedValue({ id: '1', ui_language: 'en' })
      await doLogin('a@b.com', 'pw')
      await doLogin('a@b.com', 'pw')
      setLocale('tr')
      expect(updateLanguage).toHaveBeenCalledTimes(1)
      expect(updateLanguage).toHaveBeenCalledWith('tr')
    })

    it('does not save an explicit change when signed out', () => {
      setLocale('tr')
      expect(updateLanguage).not.toHaveBeenCalled()
    })

    it('swallows a failed save and keeps the chosen language', async () => {
      const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
      updateLanguage.mockRejectedValue(new Error('network down'))
      auth.user = { id: '1', ui_language: 'en' }
      setLocale('tr')
      await vi.waitFor(() => expect(warn).toHaveBeenCalled())
      expect(document.documentElement.lang).toBe('tr')
      warn.mockRestore()
    })

    it('keeps a choice made before login when storage is unavailable', async () => {
      vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
        throw new Error('denied')
      })
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new Error('denied')
      })
      setLocale('tr')
      login.mockResolvedValue({ id: '1', ui_language: 'en' })
      await doLogin('a@b.com', 'pw')
      expect(document.documentElement.lang).toBe('tr')
      expect(updateLanguage).toHaveBeenCalledWith('tr')
      vi.restoreAllMocks()
      setLocale('en') // stored again: the page-view memory is no longer needed
    })

    it('follows another tab without writing the account again', async () => {
      me.mockResolvedValue({ id: '1', ui_language: 'en' })
      await refresh()
      localStorage.setItem('lang', 'tr')
      window.dispatchEvent(new StorageEvent('storage', { key: 'lang', newValue: 'tr' }))
      expect(document.documentElement.lang).toBe('tr')
      expect(updateLanguage).not.toHaveBeenCalled()
    })

    it('leaves the on-screen language alone on logout', async () => {
      setLocale('tr')
      logout.mockResolvedValue(null)
      await doLogout()
      expect(document.documentElement.lang).toBe('tr')
    })
  })
})
