// The landing ask field hands its question to the app through `/app?q=`.
const MAX_LENGTH = 4000

export function askTarget(text) {
  const q = String(text ?? '')
    .trim()
    .slice(0, MAX_LENGTH)
  return q ? `/app?q=${encodeURIComponent(q)}` : null
}

export function questionFromQuery(q) {
  return typeof q === 'string' ? q.trim().slice(0, MAX_LENGTH) : ''
}
