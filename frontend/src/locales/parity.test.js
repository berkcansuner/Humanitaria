import { describe, it, expect } from 'vitest'
import en from './en.json'
import tr from './tr.json'

function flatten(obj, prefix = '') {
  return Object.entries(obj).flatMap(([k, v]) =>
    v && typeof v === 'object' ? flatten(v, `${prefix}${k}.`) : [[`${prefix}${k}`, v]],
  )
}
const placeholders = (s) => [...String(s).matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

const enFlat = Object.fromEntries(flatten(en))
const trFlat = Object.fromEntries(flatten(tr))

describe('locale parity', () => {
  it('has identical key sets', () => {
    expect(Object.keys(trFlat).sort()).toEqual(Object.keys(enFlat).sort())
  })

  it('has no empty values', () => {
    for (const flat of [enFlat, trFlat]) {
      for (const [key, value] of Object.entries(flat)) {
        expect(value, key).not.toBe('')
      }
    }
  })

  it('has matching placeholders per key', () => {
    for (const key of Object.keys(enFlat)) {
      expect(placeholders(trFlat[key]), key).toEqual(placeholders(enFlat[key]))
    }
  })
})
