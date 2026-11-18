import { t } from '../i18n/index.js'

function label(btn) {
  btn.textContent = t('chat.code.copy')
  btn.setAttribute('aria-label', t('chat.code.label'))
}

/**
 * Append a "copy" button to every <pre> code block inside a rendered message.
 *
 * Buttons are created with the DOM API (not HTML string injection) so the
 * sanitized markdown output stays the only HTML sink — no XSS surface. Call
 * after a message finishes rendering (e.g. via nextTick); it is idempotent so
 * re-running on the same root won't add duplicate buttons. A re-run also
 * relabels existing buttons in the interface language, so call it again after
 * a language switch.
 *
 * @param {HTMLElement|null} root - container holding rendered message HTML
 */
export function decorateCodeBlocks(root) {
  if (!root) return
  for (const pre of root.querySelectorAll('pre')) {
    const existing = pre.dataset.copyAttached && pre.querySelector(':scope > .copy-code')
    if (existing) {
      label(existing)
      continue
    }
    pre.dataset.copyAttached = '1'

    const btn = document.createElement('button')
    btn.className = 'copy-code'
    btn.type = 'button'
    label(btn)

    btn.addEventListener('click', () => {
      const code = pre.querySelector('code')
      // textContent preserves the exact code (whitespace/newlines); innerText
      // would normalise whitespace and is also unimplemented in jsdom.
      const text = (code || pre).textContent
      navigator.clipboard?.writeText(text)
      btn.textContent = t('chat.code.copied')
      setTimeout(() => {
        btn.textContent = t('chat.code.copy')
      }, 1500)
    })

    pre.appendChild(btn)
  }
}
