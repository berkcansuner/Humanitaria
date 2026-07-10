/**
 * Pure helpers for manipulating the local message list. Shared by Regenerate
 * (drop the last answer, re-send the last question) and Edit/resend (truncate
 * at an earlier message, then re-send). Kept pure so they're easy to unit test.
 */

/** Index of the last message with role 'user', or -1 if none. */
export function findLastUserIndex(messages) {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'user') return i
  }
  return -1
}

/**
 * Return a new array containing messages up to and including `index`.
 * A negative index yields an empty array.
 */
export function truncateAt(messages, index) {
  return messages.slice(0, Math.max(0, index + 1))
}

/**
 * The server message id to keep through when truncating before `index`: the
 * last message before it that carries a serverId. Messages without one
 * (greetings, errors, in-flight turns) aren't persisted, so they're skipped.
 * Returns 0 when nothing persisted precedes the index (delete-all).
 */
export function lastServerIdBefore(messages, index) {
  for (let i = index - 1; i >= 0; i--) {
    if (messages[i].serverId != null) return messages[i].serverId
  }
  return 0
}

/**
 * Decide the local outcome of a resend (Edit/Regenerate) given whether the
 * server-side truncate succeeded.
 *
 * - success → truncate the message list locally and signal a re-send.
 * - failure → keep every message (so the client never diverges from the server),
 *   mark only the target message with `errorMessage`, and do NOT re-send. This
 *   prevents a swallowed truncate error from producing duplicate/stale turns.
 *
 * Pure: returns a new array and never mutates the input.
 */
export function planResend(messages, targetIndex, truncateOk, errorMessage) {
  if (!truncateOk) {
    return {
      messages: messages.map((m, i) => (i === targetIndex ? { ...m, error: errorMessage } : m)),
      resend: false,
    }
  }
  return { messages: truncateAt(messages, targetIndex - 1), resend: true }
}

/** Lower-case and strip diacritics so "guvenligi" matches "güvenliği". */
function _fold(s) {
  return (s || '')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
}

/**
 * Filter conversations by a diacritic-insensitive, case-insensitive title
 * substring. Blank query → all. Folding both sides lets an ASCII query find
 * accented titles (common with multilingual humanitarian report names).
 */
export function filterConversations(conversations, query) {
  const q = _fold((query || '').trim())
  if (!q) return conversations
  return conversations.filter((c) => _fold(c.title).includes(q))
}

/** Bucket key for a conversation's updated_at relative to `now`. */
function _dateGroupKey(updatedAt, now) {
  const d = new Date(updatedAt)
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  if (d >= startOfToday) return 'today'
  const weekAgo = new Date(startOfToday.getTime() - 7 * 86400000)
  if (d >= weekAgo) return 'week'
  return 'older'
}

const _DATE_GROUPS = [
  ['today', 'Today'],
  ['week', 'This week'],
  ['older', 'Older'],
]

/**
 * Group conversations by `updated_at` into Today / This week / Older sections.
 * Returns [{ key, label, items }] for non-empty groups, in fixed order. Item order
 * within a group is preserved (the server already returns updated_at desc). `now`
 * is injected for testability (defaults to the current time).
 */
export function groupConversationsByDate(conversations, now = new Date()) {
  return _DATE_GROUPS
    .map(([key, label]) => ({
      key,
      label,
      items: conversations.filter((c) => _dateGroupKey(c.updated_at, now) === key),
    }))
    .filter((g) => g.items.length)
}
