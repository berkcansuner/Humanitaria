import en from '../locales/en.json'

const NON_CODE = new Set(['network', 'generic'])
const KNOWN_CODES = new Set(Object.keys(en.errors).filter((k) => !NON_CODE.has(k)))

/**
 * Build the Error the request helpers throw for a non-ok response: message and
 * status as before, plus `code` when the JSON body carries one (api/errors.py).
 */
export async function errorFromResponse(res, url) {
  const err = new Error(`Request failed: ${res.status} ${url}`)
  err.status = res.status
  try {
    const body = await res.json()
    if (typeof body?.code === 'string') err.code = body.code
  } catch {
    // no body or not JSON: the status alone still identifies the failure
  }
  return err
}

/**
 * Translated, user-facing text for an error: `errorMessage(err, t)` with the
 * vue-i18n `t` (useI18n().t or the exported `t`). A known `err.code` gets its
 * own message; a TypeError (fetch failed) or an error with neither status nor
 * code reads as a network problem; anything else gets the generic message, or
 * `fallbackKey` when a screen can say which action failed.
 */
export function errorMessage(err, t, fallbackKey) {
  if (err?.code && KNOWN_CODES.has(err.code)) return t(`errors.${err.code}`)
  if (err instanceof TypeError || (err?.status == null && !err?.code)) return t('errors.network')
  return t(fallbackKey || 'errors.generic')
}
