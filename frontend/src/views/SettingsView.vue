<template>
  <div class="settings">
    <header class="topbar">
      <router-link class="brand" to="/app" title="Back to chat">
        <HelpingHandLogo :size="34" :radius="11" />
        <div class="brand-text">
          <h1 class="brand-title">Humanitaria</h1>
          <span class="brand-sub">Settings</span>
        </div>
      </router-link>
      <div class="topbar-spacer"></div>
      <router-link class="back-link" to="/app"><ArrowLeft :size="16" /> Back to chat</router-link>
      <UserMenu />
    </header>

    <main class="content">
      <section class="card">
        <div class="card-head"><h2>Profile</h2></div>
        <dl class="grid">
          <div>
            <dt>Email</dt>
            <dd>{{ auth.user?.email }}</dd>
          </div>
          <div>
            <dt>Sign-in method</dt>
            <dd>{{ auth.user?.auth_provider === 'google' ? 'Google' : 'Email & password' }}</dd>
          </div>
        </dl>
        <form class="form-row" @submit.prevent="saveName">
          <label class="field">
            <span>Display name</span>
            <input v-model="nameInput" type="text" maxlength="100" required />
          </label>
          <button class="primary-btn" type="submit" :disabled="savingName || !nameDirty">
            {{ savingName ? 'Saving…' : 'Save' }}
          </button>
        </form>
        <p v-if="nameMessage" class="ok-note" role="status">{{ nameMessage }}</p>
        <p v-if="nameError" class="error-box" role="alert">{{ nameError }}</p>
      </section>

      <section class="card">
        <div class="card-head"><h2>Appearance</h2></div>
        <div class="theme-seg" role="radiogroup" aria-label="Theme">
          <button
            v-for="opt in ['light', 'dark']"
            :key="opt"
            type="button"
            role="radio"
            :aria-checked="theme === opt ? 'true' : 'false'"
            :class="['seg-btn', { active: theme === opt }]"
            @click="pickTheme(opt)"
          >
            <Sun v-if="opt === 'light'" :size="15" />
            <Moon v-else :size="15" />
            {{ opt === 'light' ? 'Light' : 'Dark' }}
          </button>
        </div>
      </section>

      <section v-if="auth.user?.has_password" class="card">
        <div class="card-head"><h2>Password</h2></div>
        <form class="form-col" @submit.prevent="submitPassword">
          <label class="field">
            <span>Current password</span>
            <input v-model="currentPw" type="password" autocomplete="current-password" required />
          </label>
          <label class="field">
            <span>New password</span>
            <input
              v-model="newPw"
              type="password"
              minlength="8"
              maxlength="72"
              autocomplete="new-password"
              required
            />
          </label>
          <label class="field">
            <span>Repeat new password</span>
            <input v-model="newPw2" type="password" autocomplete="new-password" required />
          </label>
          <button class="primary-btn" type="submit" :disabled="changingPw">
            {{ changingPw ? 'Changing…' : 'Change password' }}
          </button>
        </form>
        <p v-if="pwMessage" class="ok-note" role="status">{{ pwMessage }}</p>
        <p v-if="pwError" class="error-box" role="alert">{{ pwError }}</p>
      </section>

      <section class="card danger-card">
        <div class="card-head"><h2>Danger zone</h2></div>
        <p class="muted">
          Deleting your account permanently removes your conversations, reports and profile. This
          cannot be undone.
        </p>
        <button ref="deleteTriggerBtn" class="danger-btn" type="button" @click="openDeleteModal">
          Delete my account
        </button>
      </section>

      <div v-if="showDelete" class="modal-backdrop" @click.self="closeDeleteModal">
        <div
          class="modal"
          role="dialog"
          aria-modal="true"
          aria-label="Confirm account deletion"
          @keydown="onModalKeydown"
        >
          <h3>Delete account?</h3>
          <p class="muted">
            This permanently deletes your account and all data.
            <template v-if="auth.user?.has_password"> Enter your password to confirm.</template>
            <template v-else> Type your email address to confirm.</template>
          </p>
          <form class="form-col" @submit.prevent="confirmDelete">
            <label v-if="auth.user?.has_password" class="field">
              <span>Password</span>
              <input
                ref="deleteInputEl"
                v-model="deleteConfirm"
                type="password"
                autocomplete="current-password"
                required
              />
            </label>
            <label v-else class="field">
              <span>Email</span>
              <input ref="deleteInputEl" v-model="deleteConfirm" type="email" required />
            </label>
            <p v-if="deleteError" class="error-box" role="alert">{{ deleteError }}</p>
            <div class="modal-actions">
              <button
                ref="cancelBtnEl"
                class="ghost-btn"
                type="button"
                :disabled="deleting"
                @click="closeDeleteModal"
              >
                Cancel
              </button>
              <button ref="confirmBtnEl" class="danger-btn" type="submit" :disabled="deleting">
                {{ deleting ? 'Deleting…' : 'Delete forever' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Sun, Moon } from 'lucide-vue-next'
import HelpingHandLogo from '../components/HelpingHandLogo.vue'
import UserMenu from '../components/UserMenu.vue'
import { auth } from '../utils/authStore.js'
import { updateProfile, changePassword, deleteAccount } from '../utils/authApi.js'
import { getInitialTheme, setTheme } from '../utils/theme.js'

const router = useRouter()

// --- profile ---
const nameInput = ref(auth.user?.name || '')
const savingName = ref(false)
const nameMessage = ref('')
const nameError = ref('')
const nameDirty = computed(
  () => nameInput.value.trim() && nameInput.value.trim() !== auth.user?.name,
)

async function saveName() {
  savingName.value = true
  nameMessage.value = ''
  nameError.value = ''
  try {
    auth.user = await updateProfile(nameInput.value.trim())
    nameInput.value = auth.user.name
    nameMessage.value = 'Name updated.'
  } catch {
    nameError.value = 'Could not update your name. Please try again.'
  } finally {
    savingName.value = false
  }
}

// --- appearance ---
const theme = ref(getInitialTheme())
function pickTheme(opt) {
  theme.value = opt
  setTheme(opt)
}

// --- password ---
const currentPw = ref('')
const newPw = ref('')
const newPw2 = ref('')
const changingPw = ref(false)
const pwMessage = ref('')
const pwError = ref('')

async function submitPassword() {
  pwMessage.value = ''
  pwError.value = ''
  if (newPw.value !== newPw2.value) {
    pwError.value = 'New passwords do not match.'
    return
  }
  changingPw.value = true
  try {
    await changePassword(currentPw.value, newPw.value)
    currentPw.value = newPw.value = newPw2.value = ''
    pwMessage.value = 'Password changed. Other sessions were signed out.'
  } catch (e) {
    if (e?.status === 403) pwError.value = 'Current password is incorrect.'
    else if (e?.status === 422) pwError.value = 'New password must be at least 8 characters.'
    else pwError.value = 'Could not change the password. Please try again.'
  } finally {
    changingPw.value = false
  }
}

// --- delete account ---
const showDelete = ref(false)
const deleteConfirm = ref('')
const deleting = ref(false)
const deleteError = ref('')
const deleteTriggerBtn = ref(null)
const deleteInputEl = ref(null)
const cancelBtnEl = ref(null)
const confirmBtnEl = ref(null)

function openDeleteModal() {
  deleteConfirm.value = ''
  deleteError.value = ''
  showDelete.value = true
  nextTick(() => deleteInputEl.value?.focus())
}

function closeDeleteModal() {
  if (deleting.value) return
  showDelete.value = false
  deleteConfirm.value = ''
  deleteError.value = ''
  nextTick(() => deleteTriggerBtn.value?.focus())
}

function onModalKeydown(e) {
  if (e.key === 'Escape') {
    if (deleting.value) return
    closeDeleteModal()
    return
  }
  if (e.key !== 'Tab') return
  const focusable = [deleteInputEl.value, cancelBtnEl.value, confirmBtnEl.value].filter(Boolean)
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

async function confirmDelete() {
  deleting.value = true
  deleteError.value = ''
  const body = auth.user?.has_password
    ? { password: deleteConfirm.value }
    : { confirm_email: deleteConfirm.value }
  try {
    await deleteAccount(body)
    auth.user = null
    router.push('/')
  } catch (e) {
    if (e?.status === 403) deleteError.value = 'Password is incorrect.'
    else if (e?.status === 400) deleteError.value = 'Email confirmation does not match.'
    else deleteError.value = 'Could not delete the account. Please try again.'
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.settings {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg);
}

.topbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background-color: var(--color-surface);
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  text-decoration: none;
}

.brand-title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--color-text);
  margin: 0;
}

.brand-sub {
  font-size: 11.5px;
  color: var(--color-muted);
}

.topbar-spacer {
  flex: 1;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  text-decoration: none;
}

.back-link:hover {
  color: var(--color-accent);
}

.content {
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.card {
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
}

.card-head h2 {
  font-family: var(--font-display);
  font-size: var(--text-base);
  color: var(--color-text);
  margin: 0 0 var(--space-3);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-3);
  margin: 0 0 var(--space-4);
}

.grid dt {
  font-size: 11.5px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-muted);
}

.grid dd {
  margin: 2px 0 0;
  font-size: var(--text-sm);
  color: var(--color-text);
}

.form-row {
  display: flex;
  align-items: flex-end;
  gap: var(--space-3);
}

.form-col {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-width: 360px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  flex: 1;
}

.field span {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.field input {
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-text);
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.field input:focus {
  outline: 2px solid var(--color-accent);
  outline-offset: -1px;
}

.primary-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-on-accent);
  background-color: var(--color-accent-container);
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  align-self: flex-start;
}

.primary-btn:hover:not(:disabled) {
  background-color: var(--color-accent);
}

.primary-btn:disabled {
  opacity: 0.55;
  cursor: default;
}

.theme-seg {
  display: inline-flex;
  gap: var(--space-1);
  padding: var(--space-1);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background-color: var(--color-bg);
}

.seg-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
}

.seg-btn.active {
  background-color: var(--color-surface);
  color: var(--color-text);
  box-shadow: var(--shadow-sm);
}

.ok-note {
  margin: var(--space-2) 0 0;
  font-size: var(--text-sm);
  color: var(--color-accent);
}

.error-box {
  margin: var(--space-2) 0 0;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-error);
  background-color: var(--color-error-bg);
  border-radius: var(--radius-md);
}

.muted {
  color: var(--color-muted);
  font-size: var(--text-sm);
}

.danger-card {
  border-color: color-mix(in oklab, var(--color-error) 45%, var(--color-border));
}

.danger-btn {
  margin-top: var(--space-3);
  padding: var(--space-2) var(--space-4);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: #fff;
  background-color: var(--color-error);
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
}

.danger-btn:disabled {
  opacity: 0.55;
  cursor: default;
}

.ghost-btn {
  padding: var(--space-2) var(--space-4);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: grid;
  place-items: center;
  z-index: 50;
}

.modal {
  width: min(420px, calc(100vw - 32px));
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
}

.modal h3 {
  margin: 0 0 var(--space-2);
  font-family: var(--font-display);
  color: var(--color-text);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
</style>
