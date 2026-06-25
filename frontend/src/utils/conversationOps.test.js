import { describe, it, expect } from 'vitest'
import {
  findLastUserIndex,
  truncateAt,
  lastServerIdBefore,
  planResend,
  filterConversations,
  groupConversationsByDate,
} from './conversationOps.js'

describe('findLastUserIndex', () => {
  it('returns the index of the last user message', () => {
    const messages = [
      { role: 'user', content: 'a' },
      { role: 'assistant', content: 'b' },
      { role: 'user', content: 'c' },
      { role: 'assistant', content: 'd' },
    ]
    expect(findLastUserIndex(messages)).toBe(2)
  })

  it('returns -1 when there is no user message', () => {
    expect(findLastUserIndex([{ role: 'assistant', content: 'x' }])).toBe(-1)
    expect(findLastUserIndex([])).toBe(-1)
  })
})

describe('truncateAt', () => {
  it('keeps messages up to and including the given index', () => {
    const messages = [
      { role: 'user', content: 'a' },
      { role: 'assistant', content: 'b' },
      { role: 'user', content: 'c' },
      { role: 'assistant', content: 'd' },
    ]
    expect(truncateAt(messages, 1)).toEqual([
      { role: 'user', content: 'a' },
      { role: 'assistant', content: 'b' },
    ])
  })

  it('returns a new array (does not mutate the input)', () => {
    const messages = [{ role: 'user', content: 'a' }, { role: 'assistant', content: 'b' }]
    const result = truncateAt(messages, 0)
    expect(result).toEqual([{ role: 'user', content: 'a' }])
    expect(messages).toHaveLength(2)
  })

  it('returns empty for a negative index', () => {
    expect(truncateAt([{ role: 'user', content: 'a' }], -1)).toEqual([])
  })
})

describe('lastServerIdBefore', () => {
  it('returns the serverId of the last persisted message before the index', () => {
    const messages = [
      { role: 'user', content: 'q1', serverId: 1 },
      { role: 'assistant', content: 'a1', serverId: 2 },
      { role: 'user', content: 'q2', serverId: 3 },
    ]
    expect(lastServerIdBefore(messages, 2)).toBe(2)
  })

  it('skips messages without a serverId (greeting/error/in-flight)', () => {
    const messages = [
      { role: 'user', content: 'q1', serverId: 1 },
      { role: 'assistant', content: 'a1', serverId: 2 },
      { role: 'user', content: 'merhaba' },        // greeting, not persisted
      { role: 'assistant', content: 'selam' },      // greeting reply, not persisted
      { role: 'user', content: 'q2' },              // the message being edited
    ]
    expect(lastServerIdBefore(messages, 4)).toBe(2)
  })

  it('returns 0 when there is no persisted message before the index', () => {
    const messages = [
      { role: 'user', content: 'merhaba' },
      { role: 'assistant', content: 'selam' },
      { role: 'user', content: 'q1' },
    ]
    expect(lastServerIdBefore(messages, 2)).toBe(0)
  })
})

describe('planResend', () => {
  const msgs = [
    { role: 'user', content: 'q1', serverId: 1 },
    { role: 'assistant', content: 'a1', serverId: 2 },
    { role: 'user', content: 'q2', serverId: 3 },
    { role: 'assistant', content: 'a2', serverId: 4 },
  ]

  it('on truncate success: truncates locally and signals resend', () => {
    const r = planResend(msgs, 2, true, 'ERR')
    expect(r.resend).toBe(true)
    expect(r.messages.map(m => m.content)).toEqual(['q1', 'a1'])
  })

  it('on truncate failure: does NOT resend and marks only the target with an error', () => {
    const r = planResend(msgs, 2, false, 'ERR')
    // Must not diverge from the server: keep every message, do not re-send.
    expect(r.resend).toBe(false)
    expect(r.messages).toHaveLength(4)
    expect(r.messages.map(m => m.content)).toEqual(['q1', 'a1', 'q2', 'a2'])
    expect(r.messages[2].error).toBe('ERR')
    expect(r.messages[0].error).toBeUndefined()
  })

  it('does not mutate the input array on failure', () => {
    planResend(msgs, 2, false, 'ERR')
    expect(msgs[2].error).toBeUndefined()
  })
})

describe('filterConversations', () => {
  const convs = [
    { id: '1', title: 'Sudan insani durum' },
    { id: '2', title: 'Yemen gıda güvenliği' },
    { id: '3', title: 'SUDAN yerinden edilme' },
  ]

  it('returns all when the query is empty or whitespace', () => {
    expect(filterConversations(convs, '')).toHaveLength(3)
    expect(filterConversations(convs, '   ')).toHaveLength(3)
  })

  it('filters by title case-insensitively', () => {
    expect(filterConversations(convs, 'sudan').map(c => c.id)).toEqual(['1', '3'])
  })

  it('returns empty when nothing matches', () => {
    expect(filterConversations(convs, 'xyz')).toEqual([])
  })

  it('folds diacritics so an ASCII query matches accented titles', () => {
    // "güvenliği" (ü, ğ) should be found by the plain query "guvenligi".
    expect(filterConversations(convs, 'guvenligi').map(c => c.id)).toEqual(['2'])
  })
})

describe('groupConversationsByDate', () => {
  const now = new Date('2026-06-01T12:00:00')
  const convs = [
    { id: 't', title: 'today', updated_at: '2026-06-01T09:00:00' },
    { id: 'w', title: 'week', updated_at: '2026-05-28T09:00:00' },
    { id: 'o', title: 'older', updated_at: '2026-04-01T09:00:00' },
  ]

  it('groups by updated_at into Bugün / Bu hafta / Daha eski in order', () => {
    const groups = groupConversationsByDate(convs, now)
    expect(groups.map(g => g.key)).toEqual(['today', 'week', 'older'])
    expect(groups.map(g => g.label)).toEqual(['Today', 'This week', 'Older'])
    expect(groups[0].items.map(c => c.id)).toEqual(['t'])
    expect(groups[1].items.map(c => c.id)).toEqual(['w'])
    expect(groups[2].items.map(c => c.id)).toEqual(['o'])
  })

  it('omits empty groups', () => {
    const groups = groupConversationsByDate([convs[0]], now)
    expect(groups).toHaveLength(1)
    expect(groups[0].key).toBe('today')
  })
})
