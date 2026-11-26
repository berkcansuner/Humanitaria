import { describe, it, expect, afterEach } from 'vitest'
import { createApp, h, nextTick, ref } from 'vue'
import { i18n } from '../i18n/index.js'
import { setLocale } from '../i18n/locale.js'
import DateField from './DateField.vue'

let app
let host
const value = ref('')

function mount(props = {}) {
  host = document.createElement('div')
  document.body.appendChild(host)
  app = createApp({
    render: () =>
      h(DateField, {
        modelValue: value.value,
        'onUpdate:modelValue': (v) => (value.value = v),
        ...props,
      }),
  })
  app.use(i18n).mount(host)
}
const textInput = () => host.querySelector('.date-text')
async function type(text) {
  textInput().value = text
  textInput().dispatchEvent(new Event('input'))
  textInput().dispatchEvent(new Event('blur'))
  await nextTick()
}

afterEach(() => {
  app.unmount()
  host.remove()
  setLocale('en')
})

describe('DateField', () => {
  it('shows its day as day.month.year whatever the browser locale', () => {
    value.value = '2026-08-25'
    mount()
    expect(textInput().value).toBe('25.08.2026')
    expect(textInput().placeholder).toBe('dd.mm.yyyy')
  })

  it('takes a typed day and gives it back as YYYY-MM-DD', async () => {
    value.value = '2026-08-25'
    mount()
    await type('1.9.2026')
    expect(value.value).toBe('2026-09-01')
    expect(textInput().value).toBe('01.09.2026')
  })

  it('moves a day outside its bounds to the nearest bound', async () => {
    value.value = '2026-08-25'
    mount({ min: '2026-01-01', max: '2026-11-26' })
    await type('01.12.2026')
    expect(value.value).toBe('2026-11-26')
    await type('01.01.2020')
    expect(value.value).toBe('2026-01-01')
  })

  it('keeps the last good day and marks text that is not a day', async () => {
    value.value = '2026-08-25'
    mount()
    await type('31.02.2026')
    expect(value.value).toBe('2026-08-25')
    expect(textInput().getAttribute('aria-invalid')).toBe('true')
    await type('')
    expect(textInput().value).toBe('25.08.2026')
    expect(textInput().getAttribute('aria-invalid')).toBeNull()
  })

  it('takes a day chosen in the calendar', async () => {
    value.value = '2026-08-25'
    mount()
    const native = host.querySelector('.date-native')
    native.value = '2026-10-03'
    native.dispatchEvent(new Event('change'))
    await nextTick()
    expect(value.value).toBe('2026-10-03')
    expect(textInput().value).toBe('03.10.2026')
  })

  it('names its placeholder and calendar button in the interface language', async () => {
    setLocale('tr')
    mount()
    await nextTick()
    expect(textInput().placeholder).toBe('gg.aa.yyyy')
    expect(host.querySelector('.date-pick').getAttribute('aria-label')).toBe('Takvimden tarih seç')
  })
})
