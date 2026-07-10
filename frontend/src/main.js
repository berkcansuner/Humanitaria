import { createApp } from 'vue'
import App from './App.vue'
// Self-hosted fonts (replaces the render-blocking Google Fonts <link>).
import '@fontsource-variable/dm-sans' // display — weights 100–1000
import '@fontsource/inter/400.css' // body
import '@fontsource/inter/600.css'
import '@fontsource/ibm-plex-mono/400.css' // mono / citations
import '@fontsource/ibm-plex-mono/500.css'
import '@fontsource/ibm-plex-mono/600.css'
import './style.css'
import './marketing/marketing.css'
import { router } from './router/index.js'
import { getInitialTheme, applyTheme } from './utils/theme.js'

// Apply the theme before mount to avoid a flash of the default (light) palette.
applyTheme(getInitialTheme())

createApp(App).use(router).mount('#app')
