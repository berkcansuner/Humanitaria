import { marked } from 'marked'

export function renderMarkdown(text) {
  if (!text) return ''
  // Strip dangerous raw HTML tags before passing to marked
  const safe = text
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
    .replace(/javascript:/gi, '')
  return marked.parse(safe, { gfm: true, breaks: true })
}
