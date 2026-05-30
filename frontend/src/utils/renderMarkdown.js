import { marked } from 'marked'
import DOMPurify from 'dompurify'

export function renderMarkdown(text) {
  if (!text) return ''
  const html = marked.parse(text, { gfm: true, breaks: true })
  return DOMPurify.sanitize(html)
}
