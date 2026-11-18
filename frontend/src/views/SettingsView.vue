<template>
  <div class="settings">
    <AppTopbar :context="t('titles.settings')" />

    <main class="content">
      <section class="card">
        <div class="card-head">
          <h2>{{ t('settings.profile.title') }}</h2>
        </div>
        <dl class="grid">
          <div>
            <dt>{{ t('settings.profile.email') }}</dt>
            <dd>{{ auth.user?.email }}</dd>
          </div>
          <div>
            <dt>{{ t('settings.profile.signIn') }}</dt>
            <dd>
              {{
                auth.user?.auth_provider === 'google'
                  ? t('settings.profile.providerGoogle')
                  : t('settings.profile.providerPassword')
              }}
            </dd>
          </div>
        </dl>
        <form class="form-row" @submit.prevent="saveName">
          <label class="field">
            <span>{{ t('settings.profile.name') }}</span>
            <input
              v-model="nameInput"
              type="text"
              maxlength="100"
              required
              :aria-invalid="nameError ? 'true' : undefined"
              :aria-describedby="nameError ? 'name-error' : undefined"
            />
          </label>
          <button class="primary-btn" type="submit" :disabled="savingName || !nameDirty">
            {{ savingName ? t('settings.profile.saving') : t('common.save') }}
          </button>
        </form>
        <p v-if="nameSaved" class="ok-note" role="status">{{ t('settings.profile.saved') }}</p>
        <p v-if="nameError" id="name-error" class="error-box" role="alert">{{ nameError }}</p>
      </section>

      <section class="card">
        <div class="card-head">
          <h2>{{ t('settings.appearance.title') }}</h2>
        </div>
        <div class="theme-seg" role="radiogroup" :aria-label="t('settings.appearance.theme')">
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
            {{ opt === 'light' ? t('settings.appearance.light') : t('settings.appearance.dark') }}
          </button>
        </div>
      </section>

      <section v-if="auth.user?.has_password" class="card">
        <div class="card-head">
          <h2>{{ t('settings.password.title') }}</h2>
        </div>
        <form class="form-col" novalidate @submit.prevent="submitPassword">
          <label class="field">
            <span>{{ t('settings.password.current') }}</span>
            <input
              ref="currentPwEl"
              v-model="currentPw"
              type="password"
              autocomplete="current-password"
              required
              v-bind="pwA11y('current')"
            />
          </label>
          <label class="field">
            <span>{{ t('settings.password.new') }}</span>
            <input
              ref="newPwEl"
              v-model="newPw"
              type="password"
              minlength="8"
              maxlength="72"
              autocomplete="new-password"
              required
              v-bind="pwA11y('new')"
            />
          </label>
          <label class="field">
            <span>{{ t('settings.password.repeat') }}</span>
            <input
              ref="newPw2El"
              v-model="newPw2"
              type="password"
              autocomplete="new-password"
              required
              v-bind="pwA11y('repeat')"
            />
          </label>
          <button class="primary-btn" type="submit" :disabled="changingPw">
            {{ changingPw ? t('settings.password.submitting') : t('settings.password.submit') }}
          </button>
        </form>
        <p v-if="pwChanged" class="ok-note" role="status">{{ t('settings.password.changed') }}</p>
        <p v-if="pwError" id="pw-error" class="error-box" role="alert">{{ pwError }}</p>
      </section>

      <section class="card">
        <div class="card-head">
          <h2>{{ t('settings.delete.title') }}</h2>
        </div>
        <p class="muted">{{ t('settings.delete.warning') }}</p>
        <button
          ref="deleteTriggerBtn"
          class="danger-quiet-btn"
          type="button"
          @click="openDeleteModal"
        >
          {{ t('settings.delete.trigger') }}
        </button>
      </section>

      <div v-if="showDelete" class="modal-backdrop" @click.self="closeDeleteModal">
        <div
          class="modal"
          role="dialog"
          aria-modal="true"
          :aria-label="t('settings.delete.dialogLabel')"
          @keydown="onModalKeydown"
        >
          <h3>{{ t('settings.delete.dialogTitle') }}</h3>
          <p class="muted">
            {{
              auth.user?.has_password
                ? t('settings.delete.bodyPassword')
                : t('settings.delete.bodyEmail')
            }}
          </p>
          <form class="form-col" novalidate @submit.prevent="confirmDelete">
            <label v-if="auth.user?.has_password" class="field">
              <span>{{ t('auth.password') }}</span>
              <input
                ref="deleteInputEl"
                v-model="deleteConfirm"
                type="password"
                autocomplete="current-password"
                required
                :aria-invalid="deleteError ? 'true' : undefined"
                :aria-describedby="deleteError ? 'delete-error' : undefined"
              />
            </label>
            <label v-else class="field">
              <span>{{ t('settings.profile.email') }}</span>
              <input
                ref="deleteInputEl"
                v-model="deleteConfirm"
                type="email"
                required
                :aria-invalid="deleteError ? 'true' : undefined"
                :aria-describedby="deleteError ? 'delete-error' : undefined"
              />
            </label>
            <p v-if="deleteError" id="delete-error" class="error-box" role="alert">
              {{ deleteError }}
            </p>
            <div class="modal-actions">
              <button
                ref="cancelBtnEl"
                class="ghost-btn"
                type="button"
                :disabled="deleting"
                @click="closeDeleteModal"
              >
                {{ t('common.cancel') }}
              </button>
              <button ref="confirmBtnEl" class="danger-btn" type="submit" :disabled="deleting">
                {{ deleting ? t('settings.delete.deleting') : t('settings.delete.confirm') }}
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
import { useI18n } from 'vue-i18n'
import { Sun, Moon } from 'lucide-vue-next'
import AppTopbar from '../components/AppTopbar.vue'
import { auth } from '../utils/authStore.js'
import { updateProfile, changePassword, deleteAccount } from '../utils/authApi.js'
import { errorMessage } from '../utils/errorMessage.js'
import { getInitialTheme, setTheme } from '../utils/theme.js'

const { t } = useI18n()
const router = useRouter()

// What went wrong stays untranslated: { key } for a form check, { err, fallback } for a
// failed request. It becomes text at render, so a language switch updates it on screen.
function problemText(p) {
  if (!p) return ''
  return p.key ? t(p.key) : errorMessage(p.err, t, p.fallback)
}

// --- profile ---
const nameInput = ref(auth.user?.name || '')
const savingName = ref(false)
const nameSaved = ref(false)
const nameProblem = ref(null)
const nameError = computed(() => problemText(nameProblem.value))
const nameDirty = computed(
  () => nameInput.value.trim() && nameInput.value.trim() !== auth.user?.name,
)

async function saveName() {
  savingName.value = true
  nameSaved.value = false
  nameProblem.value = null
  try {
    auth.user = await updateProfile(nameInput.value.trim())
    nameInput.value = auth.user.name
    nameSaved.value = true
  } catch (e) {
    nameProblem.value = { err: e, fallback: 'settings.profile.failed' }
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
const currentPwEl = ref(null)
const newPwEl = ref(null)
const newPw2El = ref(null)
const pwEls = { current: currentPwEl, new: newPwEl, repeat: newPw2El }
const changingPw = ref(false)
const pwChanged = ref(false)
const pwProblem = ref(null)
const pwField = ref(null)
const pwError = computed(() => problemText(pwProblem.value))

function pwA11y(field) {
  return pwField.value === field && pwError.value
    ? { 'aria-invalid': 'true', 'aria-describedby': 'pw-error' }
    : {}
}

async function failPassword(problem, field) {
  pwProblem.value = problem
  pwField.value = field
  await nextTick()
  pwEls[field]?.value?.focus()
}

async function submitPassword() {
  pwChanged.value = false
  pwProblem.value = null
  pwField.value = null
  if (!currentPw.value) return failPassword({ key: 'auth.validation.password' }, 'current')
  if (newPw.value.length < 8) return failPassword({ key: 'errors.weak_password' }, 'new')
  if (newPw.value !== newPw2.value) {
    return failPassword({ key: 'settings.password.mismatch' }, 'repeat')
  }
  changingPw.value = true
  try {
    await changePassword(currentPw.value, newPw.value)
    currentPw.value = newPw.value = newPw2.value = ''
    pwChanged.value = true
  } catch (e) {
    const field = { wrong_password: 'current', weak_password: 'new' }[e?.code] || null
    await failPassword({ err: e, fallback: 'settings.password.failed' }, field)
  } finally {
    changingPw.value = false
  }
}

// --- delete account ---
const showDelete = ref(false)
const deleteConfirm = ref('')
const deleting = ref(false)
const deleteProblem = ref(null)
const deleteError = computed(() => problemText(deleteProblem.value))
const deleteTriggerBtn = ref(null)
const deleteInputEl = ref(null)
const cancelBtnEl = ref(null)
const confirmBtnEl = ref(null)

function openDeleteModal() {
  deleteConfirm.value = ''
  deleteProblem.value = null
  showDelete.value = true
  nextTick(() => deleteInputEl.value?.focus())
}

function closeDeleteModal() {
  if (deleting.value) return
  showDelete.value = false
  deleteConfirm.value = ''
  deleteProblem.value = null
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
  deleteProblem.value = null
  const empty = auth.user?.has_password ? !deleteConfirm.value : !deleteConfirm.value.trim()
  if (empty) {
    deleteProblem.value = {
      key: auth.user?.has_password ? 'auth.validation.password' : 'auth.validation.email',
    }
    deleteInputEl.value?.focus()
    return
  }
  deleting.value = true
  const body = auth.user?.has_password
    ? { password: deleteConfirm.value }
    : { confirm_email: deleteConfirm.value }
  try {
    await deleteAccount(body)
    auth.user = null
    router.push('/')
  } catch (e) {
    deleteProblem.value = { err: e, fallback: 'settings.delete.failed' }
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

.content {
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
  padding: var(--space-5) var(--space-5) var(--space-8);
  display: flex;
  flex-direction: column;
}

/* Quiet Archive: settings are rows on the page, not stacked cards. Each
   section is a heading column and a content column, split by a hairline. */
.card {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  column-gap: var(--space-6);
  padding: var(--space-6) 0;
  border-top: 1px solid var(--color-border);
}

.card:first-child {
  border-top: none;
  padding-top: var(--space-2);
}

.card-head {
  grid-column: 1;
  grid-row: 1 / span 8;
}

.card > :not(.card-head) {
  grid-column: 2;
}

.card-head h2 {
  font-family: var(--font-display);
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-3);
  margin: 0 0 var(--space-4);
}

.grid dt {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
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
  background-color: var(--color-surface);
  border: 1px solid var(--color-outline);
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
  justify-self: start;
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
  margin: 0;
  max-width: 60ch;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

/* Starting a deletion is quiet; the solid red is kept for the confirm step. */
.danger-quiet-btn {
  justify-self: start;
  margin-top: var(--space-3);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-error);
  background: transparent;
  border: 1px solid color-mix(in oklch, var(--color-error) 45%, transparent);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: background-color 0.15s;
}

.danger-quiet-btn:hover {
  background-color: var(--color-error-bg);
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

@media (max-width: 640px) {
  .content {
    padding: var(--space-4) var(--space-4) var(--space-6);
  }
  .card {
    grid-template-columns: minmax(0, 1fr);
    row-gap: var(--space-3);
    padding: var(--space-5) 0;
  }
  .card-head,
  .card > :not(.card-head) {
    grid-column: 1;
    grid-row: auto;
  }
  .form-row {
    flex-wrap: wrap;
  }
}
</style>
