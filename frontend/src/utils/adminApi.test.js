import { describe, it, expect, vi } from 'vitest'
import { listUsers } from './adminApi.js'

describe('admin api client', () => {
  it('listUsers GETs /admin/users with query params', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ users: [], total: 0 }) }),
    )
    await listUsers({ q: 'ali', offset: 50, limit: 50 })
    expect(fetch).toHaveBeenCalledWith(
      '/admin/users?q=ali&offset=50&limit=50',
      expect.objectContaining({ method: 'GET', credentials: 'include' }),
    )
  })
})
