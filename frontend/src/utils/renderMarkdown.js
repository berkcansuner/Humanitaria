import { marked } from 'marked'
import DOMPurify from 'dompurify'

export function renderMarkdown(text) {
  if (!text) return ''
  const html = marked.parse(text, { gfm: true, breaks: true })
  const clean = DOMPurify.sanitize(html)
  // Turn citation markers [n] into clickable green chips. Done AFTER sanitize so
  // the injected anchors (digits only — no injection risk) are not stripped; the
  // click handler in Chat.vue scrolls to the matching source within the message.
  return clean.replace(/\[(\d+)\]/g, '<a class="cite" data-cite="$1" href="#src-$1">$1</a>')
}
