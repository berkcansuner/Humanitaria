// The landing ask field hands its question to the app through `/app?q=`. A
// sessionStorage copy survives the sign-in detours (signup, Google) that drop `q`.
export const ASK_STORAGE_KEY = 'humanitaria:ask-question'
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

export function stashQuestion(text) {
  const q = clip(String(text ?? '').trim())
  try {
    if (q) sessionStorage.setItem(ASK_STORAGE_KEY, q)
  } catch {
    // storage blocked: the `q` parameter still carries the question
  }
}

// Reads and clears the stashed question.
export function takeStashedQuestion() {
  try {
    const q = sessionStorage.getItem(ASK_STORAGE_KEY)
    sessionStorage.removeItem(ASK_STORAGE_KEY)
    return q ? clip(q) : ''
  } catch {
    return ''
  }
}

// What the composer should be filled with: `q` first, else the stash, and
// nothing when the user already typed something.
export function prefillFor(composerText, q, stashed) {
  if (composerText) return ''
  return questionFromQuery(q) || stashed || ''
}
