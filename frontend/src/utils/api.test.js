import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  listConversations,
  getMessages,
  createConversation,
  renameConversation,
  deleteConversation,
} from './api.js'

describe('conversation api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('listConversations GETs /conversations and returns json', async () => {
    const data = [{ id: 'a', title: 'A' }]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(data) }))
    const result = await listConversations()
    expect(fetch).toHaveBeenCalledWith('/conversations', expect.objectContaining({ method: 'GET' }))
    expect(result).toEqual(data)
  })

  it('getMessages GETs the messages path', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve([]) }))
    await getMessages('abc')
    expect(fetch).toHaveBeenCalledWith('/conversations/abc/messages', expect.objectContaining({ method: 'GET' }))
  })

  it('createConversation POSTs a title', async () => {
    const conv = { id: 'x', title: 'Yeni' }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(conv) }))
    const result = await createConversation('Yeni')
    expect(fetch).toHaveBeenCalledWith('/conversations', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ title: 'Yeni' }),
    }))
    expect(result).toEqual(conv)
  })

  it('renameConversation PATCHes the title', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) }))
    await renameConversation('id1', 'Yeni ad')
    expect(fetch).toHaveBeenCalledWith('/conversations/id1', expect.objectContaining({
      method: 'PATCH',
      body: JSON.stringify({ title: 'Yeni ad' }),
    }))
  })

  it('deleteConversation DELETEs and does not parse a body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))
    await deleteConversation('id1')
    expect(fetch).toHaveBeenCalledWith('/conversations/id1', expect.objectContaining({ method: 'DELETE' }))
  })

  it('throws on a non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
    await expect(listConversations()).rejects.toThrow()
  })
})
