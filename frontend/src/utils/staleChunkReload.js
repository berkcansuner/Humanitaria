/**
 * Recover from a stale SPA shell after a deploy.
 *
 * Vite dispatches `vite:preloadError` on window when a lazily imported route
 * chunk (JS or its CSS) fails to load. After a deploy the hashed chunk names
 * change, so a tab still running the previous index.html gets 404s and the
 * navigation silently does nothing. Reloading fetches the current shell.
 *
 * A timestamp in sessionStorage guards against reload loops: if a second
 * failure happens within GUARD_MS of a reload we let the error surface.
 */
const KEY = 'stale-chunk-reload-at'
const GUARD_MS = 10000

export function installStaleChunkReload(win = window, storage = sessionStorage, clock = Date) {
  win.addEventListener('vite:preloadError', (event) => {
    const now = clock.now()
    let last = 0
    try {
      last = Number(storage.getItem(KEY)) || 0
    } catch {
      last = 0
    }
    if (now - last < GUARD_MS) return
    try {
      storage.setItem(KEY, String(now))
    } catch {
      // storage unavailable (private mode / blocked) — still reload once per handler call
    }
    event.preventDefault()
    win.location.reload()
  })
}
