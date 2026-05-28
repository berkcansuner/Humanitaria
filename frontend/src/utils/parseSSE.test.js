import { describe, it, expect } from 'vitest'
import { parseSSE, safeUrl } from './parseSSE.js'

describe('parseSSE', () => {
  it('parses event and data from a single-line frame', () => {
    const result = parseSSE('event: token\ndata: {"content":"hello"}')
    expect(result).toEqual({ event: 'token', data: '{"content":"hello"}' })
  })

  it('uses "message" as default event when event: line is absent', () => {
    const result = parseSSE('data: {"content":"hello"}')
    expect(result).toEqual({ event: 'message', data: '{"content":"hello"}' })
  })

  it('returns null when there is no data: line', () => {
    const result = parseSSE('event: token\n')
    expect(result).toBeNull()
  })

  it('concatenates multi-line data: fields with \\n (SSE spec)', () => {
    const frame = 'event: token\ndata: line1\ndata: line2'
    const result = parseSSE(frame)
    expect(result.data).toBe('line1\nline2')
  })

  it('handles CRLF line endings', () => {
    const result = parseSSE('event: done\r\ndata: {}')
    expect(result).toEqual({ event: 'done', data: '{}' })
  })
})

describe('safeUrl', () => {
  it('allows https URLs', () => {
    const url = 'https://reliefweb.int/report/123'
    expect(safeUrl(url)).toBe(url)
  })

  it('allows http URLs', () => {
    const url = 'http://example.com/doc'
    expect(safeUrl(url)).toBe(url)
  })

  it('blocks javascript: URLs', () => {
    expect(safeUrl('javascript:alert(1)')).toBe('#')
  })

  it('blocks data: URLs', () => {
    expect(safeUrl('data:text/html,<script>alert(1)</script>')).toBe('#')
  })

  it('returns # for malformed URLs', () => {
    expect(safeUrl('not a url at all')).toBe('#')
  })

  it('returns # for empty string', () => {
    expect(safeUrl('')).toBe('#')
  })
})
