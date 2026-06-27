import { describe, it, expect, beforeEach, vi } from 'vitest'

vi.mock('./authApi.js', () => ({
  me: vi.fn(),
  login: vi.fn(),
  signup: vi.fn(),
  logout: vi.fn(),
}))

import { me, login, signup, logout } from './authApi.js'
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
})
