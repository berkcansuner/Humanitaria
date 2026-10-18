import { describe, it, expect, vi } from 'vitest'
import { installStaleChunkReload, isChunkLoadError } from './staleChunkReload.js'

const OLD_SHELL = '<script type="module" crossorigin src="/assets/index-old.js"></script>'
const NEW_SHELL = '<script type="module" crossorigin src="/assets/index-new.js"></script>'
const CHUNK_404 = new TypeError(
  'Failed to fetch dynamically imported module: https://x/assets/ReportsView-old.js',
)
const TO_REPORTS = { fullPath: '/reports?tab=saved' }

function makeEnv({ shell = NEW_SHELL, fetchFails = false, now = 100000, storage } = {}) {
  let onError
  const router = { onError: (fn) => (onError = fn) }
  const store = new Map()
  const win = {
    document: {
      querySelector: () => ({ getAttribute: () => '/assets/index-old.js' }),
    },
    fetch: vi.fn(async () => {
      if (fetchFails) throw new TypeError('Failed to fetch')
      return { ok: true, text: async () => shell }
    }),
    location: { assign: vi.fn() },
    sessionStorage: storage ?? {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(k, String(v)),
    },
  }
  const clock = { now: () => now }
  installStaleChunkReload(router, { win, clock })
  return {
    win,
    fail: (err = CHUNK_404, to = TO_REPORTS) => onError(err, to, { fullPath: '/' }),
    set: (t) => {
      now = t
    },
  }
}

describe('isChunkLoadError', () => {
  it.each([
    'Failed to fetch dynamically imported module: /assets/a.js',
    'error loading dynamically imported module: /assets/a.js',
    'Importing a module script failed.',
    'Unable to preload CSS for /assets/a.css',
  ])('recognises %s', (msg) => {
    expect(isChunkLoadError(new Error(msg))).toBe(true)
  })

  it('ignores unrelated navigation errors', () => {
    expect(isChunkLoadError(new Error('Network Error'))).toBe(false)
    expect(isChunkLoadError(undefined)).toBe(false)
  })
})

describe('installStaleChunkReload', () => {
  it('navigates to the route the user was opening when a new build is live', async () => {
    const { win, fail } = makeEnv()
    await fail()
    expect(win.fetch).toHaveBeenCalledWith('/', { cache: 'no-store' })
    expect(win.location.assign).toHaveBeenCalledWith('/reports?tab=saved')
  })

  it('leaves the error alone when the shell is unchanged (blocked or broken chunk)', async () => {
    const { win, fail } = makeEnv({ shell: OLD_SHELL })
    await fail()
    expect(win.location.assign).not.toHaveBeenCalled()
  })

  it('leaves the error alone when offline', async () => {
    const { win, fail } = makeEnv({ fetchFails: true })
    await fail()
    expect(win.location.assign).not.toHaveBeenCalled()
  })

  it('ignores errors that are not chunk-load failures', async () => {
    const { win, fail } = makeEnv()
    await fail(new Error('Network Error'))
    expect(win.fetch).not.toHaveBeenCalled()
    expect(win.location.assign).not.toHaveBeenCalled()
  })

  it('handles concurrent failures once', async () => {
    const { win, fail } = makeEnv()
    await Promise.all([fail(), fail()])
    expect(win.fetch).toHaveBeenCalledTimes(1)
    expect(win.location.assign).toHaveBeenCalledTimes(1)
  })

  it('does not loop: a second failure inside the guard window is left to surface', async () => {
    const { win, fail, set } = makeEnv()
    await fail()
    set(100000 + 5000)
    await fail()
    expect(win.location.assign).toHaveBeenCalledTimes(1)
  })

  it('navigates again once the guard window has passed', async () => {
    const { win, fail, set } = makeEnv()
    await fail()
    set(100000 + 60000)
    await fail()
    expect(win.location.assign).toHaveBeenCalledTimes(2)
  })

  it('still recovers when reading window.sessionStorage throws (site data blocked)', async () => {
    let onError
    const win = {
      document: { querySelector: () => ({ getAttribute: () => '/assets/index-old.js' }) },
      fetch: async () => ({ ok: true, text: async () => NEW_SHELL }),
      location: { assign: vi.fn() },
      get sessionStorage() {
        throw new DOMException('blocked', 'SecurityError')
      },
    }
    expect(() =>
      installStaleChunkReload({ onError: (fn) => (onError = fn) }, { win }),
    ).not.toThrow()
    await onError(CHUNK_404, TO_REPORTS)
    expect(win.location.assign).toHaveBeenCalledWith('/reports?tab=saved')
  })

  it('still recovers when storage methods throw', async () => {
    const broken = {
      getItem: () => {
        throw new Error('blocked')
      },
      setItem: () => {
        throw new Error('blocked')
      },
    }
    const { win, fail } = makeEnv({ storage: broken })
    await fail()
    expect(win.location.assign).toHaveBeenCalledTimes(1)
  })
})
