// The landing ask field hands its question to the app through `/app?q=`.
const MAX_LENGTH = 4000

// Cut on a code-point boundary so a surrogate pair is never split.
function clip(text) {
  return Array.from(text).slice(0, MAX_LENGTH).join('')
}

export function askTarget(text) {
  const q = clip(String(text ?? '').trim())
  return q ? `/app?q=${encodeURIComponent(q)}` : null
}

export function questionFromQuery(q) {
  return typeof q === 'string' ? clip(q.trim()) : ''
}
