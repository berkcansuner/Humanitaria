import { createI18n } from 'vue-i18n'
import en from '../locales/en.json'
import tr from '../locales/tr.json'
import { initialLocale, setLocale as applyLocale, onLocaleChange } from './locale.js'

const start = initialLocale()

export const i18n = createI18n({
  legacy: false,
  locale: start,
  fallbackLocale: 'en',
  messages: { en, tr },
  numberFormats: {
    en: { integer: { maximumFractionDigits: 0 } },
    tr: { integer: { maximumFractionDigits: 0 } },
  },
})

document.documentElement.lang = start
onLocaleChange((l) => {
  i18n.global.locale.value = l
})

export const t = (...args) => i18n.global.t(...args)

export function useLocale() {
  return { locale: i18n.global.locale, setLocale: applyLocale }
}
