import { createApp } from 'vue'
import App from './App.vue'
// Self-hosted fonts (replaces the render-blocking Google Fonts <link>).
import '@fontsource-variable/geist' // every text, app and landing
import '@fontsource-variable/geist-mono' // figures, dates and citation chips
import './style.css'
import './marketing/marketing.css'
import { router } from './router/index.js'
import { i18n } from './i18n/index.js'
import { getInitialTheme, applyTheme } from './utils/theme.js'
import { installStaleChunkReload } from './utils/staleChunkReload.js'

// A tab left open across a deploy still runs the old shell, whose lazy route
// chunks were replaced → load the target route from the new index.html.
installStaleChunkReload(router, { entry: import.meta.url })

// Apply the theme before mount to avoid a flash of the default (light) palette.
applyTheme(getInitialTheme())

createApp(App).use(router).use(i18n).mount('#app')
