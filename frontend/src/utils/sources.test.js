import { describe, it, expect } from 'vitest'
import { isValidSource } from './sources.js'

describe('isValidSource', () => {
  it('rejects a source with no url', () => {
    expect(isValidSource({ title: 'X' })).toBe(false)
  })

  it('rejects a country-metadata source whose title equals the country', () => {
    expect(
      isValidSource({ url: 'https://x', doctype: 'country', title: 'Sudan', country: 'Sudan' })
    ).toBe(false)
  })

  it('accepts a normal source with a url', () => {
    expect(isValidSource({ url: 'https://x/1', title: 'Report' })).toBe(true)
  })
})
