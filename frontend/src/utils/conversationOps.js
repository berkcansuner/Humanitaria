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
