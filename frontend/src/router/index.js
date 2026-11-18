import { createRouter, createWebHistory } from 'vue-router'

import LandingView from '../views/LandingView.vue'
import { t } from '../i18n/index.js'
import { normalizeLocale, setLocale, onLocaleChange } from '../i18n/locale.js'
import { auth, refresh, isAuthenticated, isAdmin } from '../utils/authStore.js'

const routes = [
  { path: '/', name: 'home', component: LandingView },
  {
    path: '/privacy',
    name: 'privacy',
    component: () => import('../views/PrivacyView.vue'),
    meta: { titleKey: 'titles.privacy' },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/AuthView.vue'),
    props: { mode: 'login' },
    meta: { titleKey: 'titles.login' },
  },
  {
    path: '/signup',
    name: 'signup',
    component: () => import('../views/AuthView.vue'),
    props: { mode: 'signup' },
    meta: { titleKey: 'titles.signup' },
  },
  // The chat app is the heaviest chunk and most visitors land on the marketing
  // page first, so it is lazy-loaded. It requires an authenticated session.
  {
    path: '/app',
    name: 'app',
    component: () => import('../views/ChatView.vue'),
    meta: { requiresAuth: true, titleKey: 'titles.chat' },
  },
  // M&E situation-report generator (form → streamed brief → saved reports).
  {
    path: '/reports',
    name: 'reports',
    component: () => import('../views/ReportsView.vue'),
    meta: { requiresAuth: true, titleKey: 'titles.reports' },
  },
  // Account settings: profile, appearance, password, account deletion.
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { requiresAuth: true, titleKey: 'titles.settings' },
  },
  // Admin-only ingestion status & management panel.
  {
    path: '/admin/ingestion',
    name: 'admin-ingestion',
    component: () => import('../views/AdminIngestionView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, titleKey: 'titles.admin' },
  },
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

// Each screen names itself in the tab ("Settings · Humanitaria"); people keep
// several open. Views may refine it (the reports view names the open report).
const BASE_TITLE = document.title || 'Humanitaria'
function applyTitle(route) {
  const key = route.meta.titleKey
  document.title = key ? `${t(key)} · Humanitaria` : BASE_TITLE
}
router.afterEach(applyTitle)
onLocaleChange(() => applyTitle(router.currentRoute.value))

// A shared ?lang=en|tr link is an explicit choice: apply it, then drop it from the URL.
router.beforeEach((to) => {
  const lang = normalizeLocale(to.query.lang)
  if (!lang) return
  setLocale(lang, { explicit: true })
  const query = { ...to.query }
  delete query.lang
  return { path: to.path, query, hash: to.hash, replace: true }
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
