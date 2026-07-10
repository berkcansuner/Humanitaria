import { describe, it, expect, beforeEach, vi } from 'vitest'
import { signup, login, logout, me } from './authApi.js'

describe('auth api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('signup POSTs credentials and the form fields', async () => {
    const user = { id: 'u1', email: 'a@b.com', name: 'A' }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(user) }),
    )
    const result = await signup('a@b.com', 'password123', 'A')
    expect(fetch).toHaveBeenCalledWith(
      '/auth/signup',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify({ email: 'a@b.com', password: 'password123', name: 'A' }),
      }),
    )
    expect(result).toEqual(user)
  })

  it('login POSTs credentials', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ id: 'u1' }) }),
    )
    await login('a@b.com', 'password123')
    expect(fetch).toHaveBeenCalledWith(
      '/auth/login',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify({ email: 'a@b.com', password: 'password123' }),
      }),
    )
  })

  it('logout POSTs and does not parse a 204 body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))
    const result = await logout()
    expect(fetch).toHaveBeenCalledWith(
      '/auth/logout',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
      }),
    )
    expect(result).toBeNull()
  })

  it('me GETs /auth/me with credentials', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ id: 'u1' }) }),
    )
    await me()
    expect(fetch).toHaveBeenCalledWith(
      '/auth/me',
      expect.objectContaining({
        method: 'GET',
        credentials: 'include',
      }),
    )
  })

  it('throws an error carrying the status on a non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))
    await expect(me()).rejects.toMatchObject({ status: 401 })
  })
})
