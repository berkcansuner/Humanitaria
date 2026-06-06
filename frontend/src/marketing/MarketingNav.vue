<template>
  <header class="nav">
    <div class="wrap nav-in">
      <router-link class="brand" to="/">
        <HandMark :size="34" :radius="11" />
        <span class="name">Humanitaria</span>
      </router-link>
      <nav class="nav-links">
        <router-link :to="{ path: '/', hash: '#features' }">Product</router-link>
        <router-link :to="{ path: '/', hash: '#sources' }">Sources</router-link>
        <router-link :to="{ path: '/', hash: '#citations' }">Citations</router-link>
        <router-link :to="{ path: '/', hash: '#uses' }">Use cases</router-link>
        <router-link to="/pricing">Pricing</router-link>
      </nav>
      <div class="nav-right">
        <router-link class="btn btn-text" to="/app">Log in</router-link>
        <router-link class="btn btn-solid" to="/app">Sign up</router-link>
        <button class="theme-toggle" aria-label="Toggle theme" title="Switch theme" @click="toggleTheme">
          <svg class="ico-sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
          <svg class="ico-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue'
import HandMark from './HandMark.vue'
import { getInitialTheme, setTheme } from '../utils/theme.js'

// Shares the same localStorage key + <html data-theme> as the chat app's
// ThemeToggle, so the choice carries across the whole site.
const theme = ref(getInitialTheme())

function toggleTheme() {
  const root = document.documentElement
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  root.classList.add('theme-switching')
  setTheme(theme.value)
  requestAnimationFrame(() => requestAnimationFrame(() => root.classList.remove('theme-switching')))
}
</script>
