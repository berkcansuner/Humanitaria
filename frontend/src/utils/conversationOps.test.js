import { describe, it, expect } from 'vitest'
import { findLastUserIndex, truncateAt, lastServerIdBefore } from './conversationOps.js'

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
