<template>
  <div class="mkt-scope">
    <MarketingNav />
    <main class="auth-main">
      <div class="auth-card">
        <h1 class="auth-title">{{ t(`auth.${ns}.title`) }}</h1>
        <p class="auth-sub">
          {{ t(`auth.${ns}.sub`) }}
        </p>

        <a class="btn btn-ghost auth-google" :href="'/auth/google/login'">
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"
            />
          </svg>
          {{ t('auth.google') }}
        </a>

        <div class="auth-divider">
          <span>{{ t('auth.or') }}</span>
        </div>

        <form class="auth-form" novalidate @submit.prevent="submit">
          <label v-if="isSignup" class="auth-label">
            {{ t('auth.name') }}
            <input
              id="auth-name"
              ref="nameInput"
              v-model="name"
              type="text"
              autocomplete="name"
              required
              class="auth-input"
              v-bind="fieldA11y('name')"
            />
          </label>
          <label class="auth-label">
            {{ t('auth.email') }}
            <input
              id="auth-email"
              ref="emailInput"
              v-model="email"
              type="email"
              autocomplete="email"
              required
              class="auth-input"
              v-bind="fieldA11y('email')"
            />
          </label>
          <label class="auth-label">
            {{ t('auth.password') }}
            <input
              id="auth-password"
              ref="passwordInput"
              v-model="password"
              type="password"
              :autocomplete="isSignup ? 'new-password' : 'current-password'"
              required
              minlength="8"
              class="auth-input"
              v-bind="fieldA11y('password')"
            />
          </label>

          <p v-if="error" id="auth-error" class="auth-error" role="alert">{{ error }}</p>

          <button type="submit" class="btn btn-solid btn-lg auth-submit" :disabled="loading">
            {{ loading ? t('auth.wait') : t(`auth.${ns}.submit`) }}
          </button>
        </form>

        <p class="auth-switch">
          {{ t(`auth.${ns}.switchPrompt`) }}
          <router-link :to="switchTo(isSignup ? '/login' : '/signup')">{{
            t(`auth.${ns}.switchLink`)
          }}</router-link>
        </p>
      </div>
    </main>
    <MarketingFooter />
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

import MarketingNav from '../marketing/MarketingNav.vue'
import MarketingFooter from '../marketing/MarketingFooter.vue'
import { doLogin, doSignup } from '../utils/authStore.js'
import { errorMessage } from '../utils/errorMessage.js'
import { validateAuth } from '../utils/authValidation.js'

const props = defineProps({
  mode: { type: String, default: 'login' },
})

const { t } = useI18n()
const router = useRouter()
const route = useRoute()

const isSignup = computed(() => props.mode === 'signup')
// Message-key namespace for the current mode: auth.login.* or auth.signup.*
const ns = computed(() => (isSignup.value ? 'signup' : 'login'))

const name = ref('')
const email = ref('')
const password = ref('')
const nameInput = ref(null)
const emailInput = ref(null)
const passwordInput = ref(null)
const inputs = { name: nameInput, email: emailInput, password: passwordInput }
// What went wrong, kept untranslated ({ key } for form checks, { err } for a failed
// request) so the message follows a language switch while it is on screen.
const problem = ref(null)
const invalidField = ref(null)
const error = computed(() => {
  if (!problem.value) return ''
  return problem.value.key ? t(problem.value.key) : errorMessage(problem.value.err, t)
})
const loading = ref(false)

function fieldA11y(field) {
  return invalidField.value === field && error.value
    ? { 'aria-invalid': 'true', 'aria-describedby': 'auth-error' }
    : {}
}

// The login <-> signup switch keeps `redirect`, so the landing question survives it.
function switchTo(path) {
  return typeof route.query.redirect === 'string'
    ? { path, query: { redirect: route.query.redirect } }
    : path
}

async function submit() {
  problem.value = null
  invalidField.value = null
  const invalid = validateAuth({
    isSignup: isSignup.value,
    name: name.value,
    email: email.value,
    password: password.value,
  })
  if (invalid) {
    problem.value = { key: invalid.key }
    invalidField.value = invalid.field
    await nextTick()
    inputs[invalid.field].value?.focus()
    return
  }
  loading.value = true
  try {
    if (isSignup.value) {
      await doSignup(email.value.trim(), password.value, name.value.trim())
    } else {
      await doLogin(email.value.trim(), password.value)
    }
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/app'
    router.push(redirect)
  } catch (e) {
    problem.value = { err: e }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-main {
  min-height: calc(100vh - 70px);
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  place-items: center;
  padding: 48px 28px;
}
.auth-card {
  width: 100%;
  max-width: 420px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 40px 36px;
  box-shadow: 0 18px 48px -24px rgba(0, 0, 0, 0.28);
}
.auth-title {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0;
}
.auth-sub {
  color: var(--color-text-secondary);
  font-size: 14.5px;
  margin: 8px 0 28px;
  line-height: 1.5;
}
.auth-google {
  width: 100%;
  padding: 11px 18px;
  font-size: 14.5px;
}
.auth-divider {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin: 22px 0;
  color: var(--color-muted);
  font-size: 12px;
}
.auth-divider::before,
.auth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}
.auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.auth-label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}
.auth-input {
  font-family: var(--font-body);
  font-size: 15px;
  color: var(--color-text);
  background: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: 10px;
  padding: 11px 13px;
  outline: none;
  transition:
    border-color 0.18s,
    box-shadow 0.18s;
}
.auth-input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 18%, transparent);
}
.auth-submit {
  width: 100%;
  margin-top: var(--space-1);
}
.auth-error {
  color: #ba1a1a;
  background: color-mix(in oklch, #ba1a1a 10%, transparent);
  border-radius: var(--radius-lg);
  padding: 9px 12px;
  font-size: 13px;
  margin: 0;
}
.auth-switch {
  margin: 24px 0 0;
  text-align: center;
  font-size: 14px;
  color: var(--color-text-secondary);
}
.auth-switch a {
  color: var(--color-accent);
  font-weight: 600;
}
.auth-switch a:hover {
  text-decoration: underline;
}
</style>
