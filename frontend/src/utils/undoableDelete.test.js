import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useUndoableDelete } from './undoableDelete.js'

describe('useUndoableDelete', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  function setup(overrides = {}) {
    const calls = { commit: [], committed: [], errors: [], undone: [] }
    const api = useUndoableDelete({
      delay: 5000,
      commit: async (id) => calls.commit.push(id),
      onCommitted: (id) => calls.committed.push(id),
      onError: (e, id) => calls.errors.push([e.message, id]),
      onUndo: (id, meta) => calls.undone.push([id, meta]),
      ...overrides,
    })
    return { api, calls }
  }

  it('hides the item at once and deletes only after the undo window', async () => {
    const { api, calls } = setup()
    api.remove('a')
    expect(api.hiddenIds.value.has('a')).toBe(true)
    expect(api.pending.value).toEqual({ id: 'a', meta: null })
    expect(calls.commit).toEqual([])

    await vi.advanceTimersByTimeAsync(5000)
    expect(calls.commit).toEqual(['a'])
    expect(calls.committed).toEqual(['a'])
    expect(api.pending.value).toBe(null)
    expect(api.hiddenIds.value.has('a')).toBe(false)
  })

  it('undo restores the item and never calls the server', async () => {
    const { api, calls } = setup()
    api.remove('a', { wasActive: true })
    api.undo()
    await vi.advanceTimersByTimeAsync(10000)
    expect(calls.commit).toEqual([])
    expect(calls.undone).toEqual([['a', { wasActive: true }]])
    expect(api.hiddenIds.value.has('a')).toBe(false)
    expect(api.pending.value).toBe(null)
  })

  it('a second delete commits the first one immediately', async () => {
    const { api, calls } = setup()
    api.remove('a')
    await api.remove('b')
    expect(calls.commit).toEqual(['a'])
    expect(api.pending.value.id).toBe('b')
    expect(api.hiddenIds.value.has('b')).toBe(true)
  })

  it('flush commits the pending delete right away (e.g. on unmount)', async () => {
    const { api, calls } = setup()
    api.remove('a')
    await api.flush()
    expect(calls.commit).toEqual(['a'])
    expect(api.pending.value).toBe(null)
  })

  it('a failed delete brings the item back and reports the error', async () => {
    const { api, calls } = setup({
      commit: async () => {
        throw new Error('HTTP 500')
      },
    })
    api.remove('a')
    await vi.advanceTimersByTimeAsync(5000)
    expect(calls.errors).toEqual([['HTTP 500', 'a']])
    expect(calls.committed).toEqual([])
    expect(api.hiddenIds.value.has('a')).toBe(false)
  })

  it('undo and flush are no-ops with nothing pending', async () => {
    const { api, calls } = setup()
    api.undo()
    await api.flush()
    expect(calls.commit).toEqual([])
    expect(calls.undone).toEqual([])
  })
})
