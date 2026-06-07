<template>
  <div class="mkt-scope">
    <MarketingNav />
    <main class="auth-main">
      <div class="auth-card">
        <h1 class="auth-title">{{ isSignup ? 'Create your account' : 'Welcome back' }}</h1>
        <p class="auth-sub">
          {{ isSignup
            ? 'Start asking the humanitarian record — answers you can cite.'
            : 'Sign in to continue to Humanitaria.' }}
        </p>

        <a class="btn btn-ghost auth-google" :href="'/auth/google/login'">
          <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z"/><path fill="#FBBC05" d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/></svg>
          Continue with Google
        </a>

        <div class="auth-divider"><span>or</span></div>

        <form class="auth-form" @submit.prevent="submit">
          <label v-if="isSignup" class="auth-label">
            Name
            <input v-model="name" type="text" autocomplete="name" required class="auth-input" />
          </label>
          <label class="auth-label">
            Email
            <input v-model="email" type="email" autocomplete="email" required class="auth-input" />
          </label>
          <label class="auth-label">
            Password
            <input
              v-model="password"
              type="password"
              :autocomplete="isSignup ? 'new-password' : 'current-password'"
              required
              minlength="8"
              class="auth-input"
            />
          </label>

          <p v-if="error" class="auth-error">{{ error }}</p>

          <button type="submit" class="btn btn-solid btn-lg auth-submit" :disabled="loading">
            {{ loading ? 'Please wait…' : (isSignup ? 'Create account' : 'Log in') }}
          </button>
        </form>

        <p class="auth-switch">
          <template v-if="isSignup">
            Already have an account?
            <router-link to="/login">Log in</router-link>
          </template>
          <template v-else>
            New to Humanitaria?
            <router-link to="/signup">Sign up</router-link>
          </template>
        </p>
      </div>
    </main>
    <MarketingFooter />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

import MarketingNav from '../marketing/MarketingNav.vue'
import MarketingFooter from '../marketing/MarketingFooter.vue'
import { doLogin, doSignup } from '../utils/authStore.js'

const props = defineProps({
  mode: { type: String, default: 'login' },
})

const router = useRouter()
const route = useRoute()

const isSignup = computed(() => props.mode === 'signup')

const name = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

function messageFor(status) {
  if (status === 409) return 'An account with this email already exists.'
  if (status === 401) return 'Invalid email or password.'
  if (status === 422) return 'Please check your details — password must be at least 8 characters.'
  return 'Something went wrong. Please try again.'
}

async function submit() {
  error.value = ''
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
    error.value = messageFor(e?.status)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-main {
  min-height: calc(100vh - 70px);
  display: grid;
  place-items: center;
  padding: 48px 28px;
}
.auth-card {
  width: 100%;
  max-width: 420px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 40px 36px;
  box-shadow: 0 18px 48px -24px rgba(0, 0, 0, 0.28);
}
.auth-title {
  font-family: var(--font);
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0;
}
.auth-sub {
  color: var(--text-2);
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
  gap: 12px;
  margin: 22px 0;
  color: var(--muted);
  font-size: 12px;
}
.auth-divider::before,
.auth-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--border);
}
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.auth-label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-2);
}
.auth-input {
  font-family: var(--body);
  font-size: 15px;
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  padding: 11px 13px;
  outline: none;
  transition: border-color 0.18s, box-shadow 0.18s;
}
.auth-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--accent) 18%, transparent);
}
.auth-submit {
  width: 100%;
  margin-top: 4px;
}
.auth-error {
  color: #ba1a1a;
  background: color-mix(in oklch, #ba1a1a 10%, transparent);
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 13px;
  margin: 0;
}
.auth-switch {
  margin: 24px 0 0;
  text-align: center;
  font-size: 14px;
  color: var(--text-2);
}
.auth-switch a {
  color: var(--accent);
  font-weight: 600;
}
.auth-switch a:hover {
  text-decoration: underline;
}
</style>
