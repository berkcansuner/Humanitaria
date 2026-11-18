import { describe, it, expect, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import en from '../locales/en.json'
import tr from '../locales/tr.json'
import { errorMessage, errorFromResponse } from './errorMessage.js'

function tFor(locale) {
  return createI18n({ legacy: false, locale, fallbackLocale: 'en', messages: { en, tr } }).global.t
}

describe('errorMessage', () => {
  it('translates a known code in the active language', () => {
    expect(errorMessage({ code: 'email_taken' }, tFor('tr'))).toBe(tr.errors.email_taken)
    expect(errorMessage({ code: 'email_taken' }, tFor('en'))).toBe(en.errors.email_taken)
    expect(tr.errors.email_taken).toBe('Bu e-posta adresiyle zaten bir hesap var.')
  })

  it('falls back to the generic message for an unknown code or no code', () => {
    const t = tFor('tr')
    expect(errorMessage({ code: 'something_new', status: 400 }, t)).toBe(tr.errors.generic)
    expect(errorMessage({ status: 500 }, t)).toBe(tr.errors.generic)
  })

  it('treats an unknown code without a status (an SSE error event) as generic, not network', () => {
    expect(errorMessage({ code: 'future_code' }, tFor('en'))).toBe(en.errors.generic)
    expect(errorMessage({ code: 'future_code' }, tFor('tr'))).toBe(tr.errors.generic)
  })

  it('does not treat the reserved network/generic keys as server codes', () => {
    expect(errorMessage({ code: 'network', status: 400 }, tFor('en'))).toBe(en.errors.generic)
  })

  it('reports a network problem for a TypeError or an error without a status', () => {
    const t = tFor('en')
    expect(errorMessage(new TypeError('Failed to fetch'), t)).toBe(en.errors.network)
    expect(errorMessage(new Error('offline'), t)).toBe(en.errors.network)
  })

  it('has a message for every code the API can send', () => {
    const codes = [
      'not_authenticated',
      'forbidden',
      'invalid_credentials',
      'email_taken',
      'weak_password',
      'wrong_password',
      'email_mismatch',
      'not_found',
      'rate_limited',
      'message_empty',
      'message_too_long',
      'conversation_limit',
      'report_limit',
      'series_mismatch',
      'model_busy',
      'quota_exhausted',
      'report_failed',
      'chat_failed',
      'body_too_large',
      'validation_failed',
      'ingest_running',
    ]
    for (const code of codes) {
      expect(en.errors[code], code).toBeTruthy()
      expect(tr.errors[code], code).toBeTruthy()
    }
  })
})

describe('errorMessage with a fallback key', () => {
  it('replaces only the generic message with the screen-specific one', () => {
    const t = tFor('tr')
    expect(errorMessage({ status: 500 }, t, 'admin.errors.start')).toBe(tr.admin.errors.start)
    expect(errorMessage({ code: 'ingest_running', status: 409 }, t, 'admin.errors.start')).toBe(
      tr.errors.ingest_running,
    )
    expect(errorMessage(new TypeError('x'), t, 'admin.errors.start')).toBe(tr.errors.network)
  })
})

describe('errorFromResponse', () => {
  it('carries status and the code from the JSON body', async () => {
    const res = { status: 409, json: async () => ({ detail: 'x', code: 'email_taken' }) }
    const err = await errorFromResponse(res, '/auth/signup')
    expect(err.message).toBe('Request failed: 409 /auth/signup')
    expect(err.status).toBe(409)
    expect(err.code).toBe('email_taken')
  })

  it('still builds the error when the body is missing or not JSON', async () => {
    const bad = { status: 502, json: vi.fn().mockRejectedValue(new SyntaxError('bad')) }
    expect((await errorFromResponse(bad, '/x')).code).toBeUndefined()
    expect((await errorFromResponse({ status: 500 }, '/x')).status).toBe(500)
  })
})
