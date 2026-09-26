import { describe, it, expect, vi } from 'vitest'
import { installStaleChunkReload } from './staleChunkReload.js'

function makeEnv(now = 100000) {
  const listeners = {}
  const store = new Map()
  const win = {
    addEventListener: (type, fn) => { listeners[type] = fn },
    location: { reload: vi.fn() },
  }
  const storage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
  }
  const clock = { now: () => now }
  installStaleChunkReload(win, storage, clock)
  const fire = () => {
    const ev = { preventDefault: vi.fn() }
    listeners['vite:preloadError'](ev)
    return ev
  }
  return { win, storage, fire, clock, set: (t) => { now = t } }
}

describe('installStaleChunkReload', () => {
  it('reloads once when a chunk fails to load (stale shell after a deploy)', () => {
    const { win, fire } = makeEnv()
    const ev = fire()
    expect(ev.preventDefault).toHaveBeenCalled()
    expect(win.location.reload).toHaveBeenCalledTimes(1)
  })

  it('does not loop: a second failure right after a reload is left to surface', () => {
    const { win, fire } = makeEnv()
    fire()
    const ev = fire()
    expect(win.location.reload).toHaveBeenCalledTimes(1)
    expect(ev.preventDefault).not.toHaveBeenCalled()
  })

  it('reloads again once the guard window has passed', () => {
    const { win, fire, set } = makeEnv(100000)
    fire()
    set(100000 + 60000)
    fire()
    expect(win.location.reload).toHaveBeenCalledTimes(2)
  })

  it('still reloads when sessionStorage is unavailable', () => {
    const listeners = {}
    const win = { addEventListener: (t, fn) => { listeners[t] = fn }, location: { reload: vi.fn() } }
    const broken = { getItem: () => { throw new Error('blocked') }, setItem: () => { throw new Error('blocked') } }
    installStaleChunkReload(win, broken, { now: () => 100000 })
    listeners['vite:preloadError']({ preventDefault: vi.fn() })
    expect(win.location.reload).toHaveBeenCalledTimes(1)
  })
})
