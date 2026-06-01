/**
 * Append a "copy" button to every <pre> code block inside a rendered message.
 *
 * Buttons are created with the DOM API (not HTML string injection) so the
 * sanitized markdown output stays the only HTML sink — no XSS surface. Call
 * after a message finishes rendering (e.g. via nextTick); it is idempotent so
 * re-running on the same root won't add duplicate buttons.
 *
 * @param {HTMLElement|null} root - container holding rendered message HTML
 */
export function decorateCodeBlocks(root) {
  if (!root) return
  for (const pre of root.querySelectorAll('pre')) {
    if (pre.dataset.copyAttached) continue
    pre.dataset.copyAttached = '1'

    const btn = document.createElement('button')
    btn.className = 'copy-code'
    btn.type = 'button'
    btn.textContent = 'Copy'
    btn.setAttribute('aria-label', 'Copy code')

    btn.addEventListener('click', () => {
      const code = pre.querySelector('code')
      // textContent preserves the exact code (whitespace/newlines); innerText
      // would normalise whitespace and is also unimplemented in jsdom.
      const text = (code || pre).textContent
      navigator.clipboard?.writeText(text)
      const prev = btn.textContent
      btn.textContent = 'Copied'
      setTimeout(() => { btn.textContent = prev }, 1500)
    })

    pre.appendChild(btn)
  }
}
