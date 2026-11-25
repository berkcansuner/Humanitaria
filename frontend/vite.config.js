import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import react from '@vitejs/plugin-react'
import { privacyHtml, withStaticContent } from './scripts/staticPages.js'
import { PRIVACY_EMAIL } from './src/contact.js'

// dist/privacy.html: the built shell with the privacy policy's text for readers
// that do not run JavaScript; api/main.py serves it for /privacy.
function staticPages() {
  let root, outDir
  return {
    name: 'static-pages',
    apply: 'build',
    configResolved(config) {
      root = config.root
      outDir = resolve(root, config.build.outDir)
    },
    closeBundle() {
      const en = JSON.parse(readFileSync(resolve(root, 'src/locales/en.json'), 'utf8'))
      const shell = readFileSync(resolve(outDir, 'index.html'), 'utf8')
      const page = withStaticContent(shell, privacyHtml(en.privacy, PRIVACY_EMAIL))
      writeFileSync(resolve(outDir, 'privacy.html'), page)
    },
  }
}

export default defineConfig({
  // plugin-react is scoped to .jsx/.tsx so it never touches .vue files or
  // Vue's compiled script blocks — the React island lives only in *.jsx.
  plugins: [vue(), react({ include: /\.(jsx|tsx)$/ }), staticPages()],
  // vue-i18n build flags (boolean literals): the app uses the Composition API
  // only, so the legacy API is tree-shaken. FULL_INSTALL stays on — it registers
  // the global <i18n-t> component the templates use.
  define: {
    __VUE_I18N_LEGACY_API__: false,
    __VUE_I18N_FULL_INSTALL__: true,
    __INTLIFY_PROD_DEVTOOLS__: false,
  },
  server: {
    port: 5173,
    proxy: {
      '/chat': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/auth': 'http://127.0.0.1:8000',
      '/conversations': 'http://127.0.0.1:8000',
    },
  },
})
