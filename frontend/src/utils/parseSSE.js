/**
 * Parse a single SSE frame (lines between blank lines) into {event, data}.
 * Handles multi-line data: fields per the SSE spec (concatenated with \n).
 * Returns null if the frame contains no data: line.
 */
export function parseSSE(chunk) {
  let event = null
  const dataLines = []
  for (const line of chunk.split(/\r?\n/)) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
    }
  }
  if (dataLines.length > 0) {
    return { event: event || 'message', data: dataLines.join('\n') }
  }
  return null
}

/**
 * Allow only http(s) URLs to prevent javascript: / data: XSS vectors.
 * Returns '#' for any non-http(s) or malformed URL.
 */
export function safeUrl(url) {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? url : '#'
  } catch {
    return '#'
  }
}
