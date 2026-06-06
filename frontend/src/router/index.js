import { createRouter, createWebHistory } from 'vue-router'

import LandingView from '../views/LandingView.vue'

const routes = [
  { path: '/', name: 'home', component: LandingView },
  // The chat app is the heaviest chunk and most visitors land on the marketing
  // page first, so it is lazy-loaded.
  { path: '/app', name: 'app', component: () => import('../views/ChatView.vue') },
  // Unknown paths fall back to the landing page.
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // Anchor links (e.g. /#features) scroll to the section, offset for the
    // 70px sticky nav. Returning a promise lets a cross-page jump wait for
    // the destination view to mount.
    if (to.hash) {
      return { el: to.hash, top: 80, behavior: 'smooth' }
    }
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
})
