/**
 * Recover from a stale SPA shell after a deploy.
 *
 * Each deploy replaces the hashed /assets chunks, so a tab still running the
 * previous index.html gets 404s when it lazily loads a route and the click
 * silently does nothing. When a route chunk fails to load we fetch the current
 * shell: if it no longer references our entry script a new build is live, so
 * we hard-navigate to the page the user was opening (location.reload() would
 * land back on the page they were leaving — the failed navigation never
 * changed the URL). If the shell is unchanged or unreachable (offline, a
 * blocked or broken chunk) it isn't a deploy and the error is left to surface.
 *
 * Only router navigations are handled: an async component failing inside a
 * view (e.g. the chat's suggestion card) must not reload the page under the user.
 *
 * A timestamp in sessionStorage is a second guard against reload loops.
 */
const KEY = 'stale-chunk-reload-at'
const GUARD_MS = 10000

// Chromium, Firefox, Safari, and Vite's CSS preload failure respectively.
const CHUNK_ERROR =
  /Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed|Unable to preload CSS/i

export function isChunkLoadError(err) {
  return CHUNK_ERROR.test(String(err?.message ?? err ?? ''))
}

/** src of the running page's entry module, e.g. /assets/index-abc123.js */
function currentEntry(doc) {
  return doc.querySelector('script[type="module"][src]')?.getAttribute('src') ?? null
}

async function newBuildIsLive(win, entry) {
  if (!entry) return false
  try {
    const res = await win.fetch('/', { cache: 'no-store' })
    if (!res.ok) return false
    return !(await res.text()).includes(entry)
  } catch {
    return false // offline / blocked → not a deploy
  }
}

function sessionStore(win) {
  // Merely reading window.sessionStorage throws when site data is blocked.
  try {
    return win.sessionStorage
  } catch {
    return null
  }
}

export function installStaleChunkReload(router, { win = window, clock = Date } = {}) {
  let pending = false
  router.onError(async (err, to) => {
    if (pending || !to || !isChunkLoadError(err)) return
    pending = true
    try {
      if (!(await newBuildIsLive(win, currentEntry(win.document)))) return
      const storage = sessionStore(win)
      const now = clock.now()
      let last = 0
      try {
        last = Number(storage?.getItem(KEY)) || 0
      } catch {
        last = 0
      }
      if (now - last < GUARD_MS) return
      try {
        storage?.setItem(KEY, String(now))
      } catch {
        // storage unavailable — the shell comparison alone prevents a loop
      }
      win.location.assign(to.fullPath)
    } finally {
      pending = false
    }
  })
}
