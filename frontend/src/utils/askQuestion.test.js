import { describe, it, expect } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import { askTarget, questionFromQuery } from './askQuestion.js'

describe('askTarget', () => {
  it('returns null for empty or whitespace text', () => {
    expect(askTarget('  ')).toBeNull()
  })
  it('encodes the trimmed question into the app url', () => {
    expect(askTarget('Sudan IDPs')).toBe('/app?q=Sudan%20IDPs')
  })
  it('cuts text over 4000 characters to 4000', () => {
    expect(askTarget('a'.repeat(5000))).toBe('/app?q=' + 'a'.repeat(4000))
  })
})

describe('questionFromQuery', () => {
  it('ignores non-string values', () => {
    expect(questionFromQuery(['a'])).toBe('')
  })
  it('trims strings', () => {
    expect(questionFromQuery(' x ')).toBe('x')
  })
})

describe('login round-trip', () => {
  it('the question survives the guard redirect and the post-login push', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/app', component: {} },
        { path: '/login', component: {} },
      ],
    })
    // router guard: redirect = to.fullPath
    await router.push(askTarget('Sudan IDPs & food'))
    const fullPath = router.currentRoute.value.fullPath
    await router.push({ path: '/login', query: { redirect: fullPath } })
    // AuthView: router.push(route.query.redirect)
    await router.push(router.currentRoute.value.query.redirect)
    expect(questionFromQuery(router.currentRoute.value.query.q)).toBe('Sudan IDPs & food')
  })
})
