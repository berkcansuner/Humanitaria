// Text for readers that do not run JavaScript. The app is a single-page app, so
// without JS every route is an empty shell, and Google's OAuth brand check found
// no home page purpose and no privacy policy. The build writes the page text into
// a <noscript> block: index.html carries the home text by hand, and privacy.html
// (served for /privacy by api/main.py) is the built shell with the English policy
// from locales/en.json, so the policy has one source.

const NOSCRIPT = /<noscript id="static-content">[\s\S]*?<\/noscript>/

const escapeHtml = (s) =>
  String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')

// A message with its {name} slots filled by ready-made HTML; the rest is escaped.
function fill(message, slots = {}) {
  return message
    .split(/(\{\w+\})/)
    .map((part) => {
      const name = /^\{(\w+)\}$/.exec(part)?.[1]
      if (name === undefined) return escapeHtml(part)
      if (!(name in slots)) throw new Error(`privacy: no value for {${name}}`)
      return slots[name]
    })
    .join('')
}

const item = (l, slots) => `<li><strong>${escapeHtml(l.lead)}</strong> ${fill(l.text, slots)}</li>`

/** The privacy policy as plain HTML, from the `privacy` messages of en.json. */
export function privacyHtml(p, email) {
  const policyUrl = 'https://developers.google.com/terms/api-services-user-data-policy'
  return [
    `<h1>${escapeHtml(p.title)}</h1>`,
    `<p>${escapeHtml(p.updated)}</p>`,
    `<p>${escapeHtml(p.intro)}</p>`,
    `<h2>${escapeHtml(p.s1.title)}</h2>`,
    '<ul>',
    item(p.s1.l1),
    item(p.s1.l2),
    item(p.s1.l3),
    item(p.s1.l4, { cookie: '<code>rw_session</code>' }),
    '</ul>',
    `<p>${escapeHtml(p.s1.after)}</p>`,
    `<h2>${escapeHtml(p.s2.title)}</h2>`,
    `<p>${fill(p.s2.p1, { policy: `<a href="${policyUrl}">${escapeHtml(p.s2.policyLink)}</a>` })}</p>`,
    `<h2>${escapeHtml(p.s3.title)}</h2>`,
    '<ul>',
    item(p.s3.l1),
    item(p.s3.l2),
    item(p.s3.l3),
    item(p.s3.l4),
    '</ul>',
    `<p>${escapeHtml(p.s3.after)}</p>`,
    `<h2>${escapeHtml(p.s4.title)}</h2>`,
    `<p>${fill(p.s4.p1, { path: `<strong>${escapeHtml(p.s4.path)}</strong>` })}</p>`,
    `<h2>${escapeHtml(p.s5.title)}</h2>`,
    `<p>${fill(p.s5.p1, { email: `<a href="mailto:${email}">${escapeHtml(email)}</a>` })}</p>`,
    `<h2>${escapeHtml(p.s6.title)}</h2>`,
    `<p>${escapeHtml(p.s6.p1)}</p>`,
    `<h2>${escapeHtml(p.s7.title)}</h2>`,
    `<p>${escapeHtml(p.s7.p1)}</p>`,
  ].join('\n')
}

/** The shell with its <noscript id="static-content"> block replaced by `inner`. */
export function withStaticContent(html, inner) {
  if (!NOSCRIPT.test(html)) throw new Error('index.html has no <noscript id="static-content">')
  return html.replace(
    NOSCRIPT,
    () => `<noscript id="static-content"><main>\n${inner}\n</main></noscript>`,
  )
}
