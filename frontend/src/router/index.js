import { createRouter, createWebHistory } from 'vue-router'

import LandingView from '../views/LandingView.vue'
import { auth, refresh, isAuthenticated, isAdmin } from '../utils/authStore.js'

const routes = [
  { path: '/', name: 'home', component: LandingView },
  { path: '/login', name: 'login', component: () => import('../views/AuthView.vue'), props: { mode: 'login' } },
  { path: '/signup', name: 'signup', component: () => import('../views/AuthView.vue'), props: { mode: 'signup' } },
  // The chat app is the heaviest chunk and most visitors land on the marketing
  // page first, so it is lazy-loaded. It requires an authenticated session.
  { path: '/app', name: 'app', component: () => import('../views/ChatView.vue'), meta: { requiresAuth: true } },
  // Admin-only ingestion status & management panel.
  { path: '/admin/ingestion', name: 'admin-ingestion', component: () => import('../views/AdminIngestionView.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
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

router.beforeEach(async (to) => {
  // Resolve the session once (on first navigation / hard refresh).
  if (!auth.ready) await refresh()

  if (to.meta.requiresAuth && !isAuthenticated()) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  // Admin-only pages (e.g. the ingestion panel) require an allowlisted account.
  if (to.meta.requiresAdmin && !isAdmin()) {
    return { path: '/app' }
  }
  // Signed-in users have no reason to see the auth pages.
  if ((to.name === 'login' || to.name === 'signup') && isAuthenticated()) {
    return { path: '/app' }
  }
})
