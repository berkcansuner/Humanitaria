import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
import './marketing/marketing.css'
import { router } from './router/index.js'
import { getInitialTheme, applyTheme } from './utils/theme.js'

// Apply the theme before mount to avoid a flash of the default (light) palette.
applyTheme(getInitialTheme())

createApp(App).use(router).mount('#app')
