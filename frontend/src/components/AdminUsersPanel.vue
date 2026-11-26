<template>
  <section class="card">
    <div class="card-head">
      <h2>{{ t('admin.users.title') }}</h2>
    </div>
    <p class="muted">{{ t('admin.users.text') }}</p>

    <div class="users-actions">
      <input
        v-model="query"
        class="user-search"
        type="search"
        :placeholder="t('admin.users.placeholder')"
        :aria-label="t('admin.users.searchLabel')"
        @input="onSearchInput"
      />
      <span v-if="!loading" class="users-meta">{{
        t('admin.users.count', { n: formatNumber(total) }, total)
      }}</span>
    </div>

    <div v-if="error" class="error-box" role="alert">
      {{ t('admin.users.loadFailed') }}
      <button class="retry-btn" type="button" @click="load">{{ t('admin.users.retry') }}</button>
    </div>

    <p v-if="loading && !items.length" class="muted">{{ t('common.loading') }}</p>
    <p v-else-if="!loading && !items.length" class="muted">
      <template v-if="query.trim()">{{ t('admin.users.noMatch', { q: query }) }}</template>
      <template v-else>{{ t('admin.users.none') }}</template>
    </p>

    <template v-if="items.length">
      <div class="table-scroll">
        <table class="users-table">
          <thead>
            <tr>
              <th>{{ t('admin.users.name') }}</th>
              <th>{{ t('admin.users.email') }}</th>
              <th>{{ t('admin.users.provider') }}</th>
              <th>{{ t('admin.users.admin') }}</th>
              <th>{{ t('admin.users.joined') }}</th>
              <th>{{ t('admin.users.lastLogin') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in items" :key="u.id">
              <td class="cell-name">{{ u.name || '—' }}</td>
              <td>{{ u.email }}</td>
              <td>
                {{
                  u.auth_provider === 'google'
                    ? t('admin.users.providerGoogle')
                    : t('admin.users.providerPassword')
                }}
              </td>
              <td>
                <span v-if="u.is_admin" class="role-admin">{{ t('admin.users.adminBadge') }}</span>
                <span v-else>—</span>
              </td>
              <td class="cell-date">{{ formatDate(u.created_at) }}</td>
              <td :class="{ 'cell-date': u.last_login }">
                {{ u.last_login ? formatDate(u.last_login) : '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="pageCount > 1" class="users-pager">
        <button class="pager-btn" :disabled="offset === 0" @click="prevPage">
          {{ t('admin.pager.prev') }}
        </button>
        <span class="pager-info">{{ t('admin.pager.page', { page, total: pageCount }) }}</span>
        <button class="pager-btn" :disabled="page >= pageCount" @click="nextPage">
          {{ t('admin.pager.next') }}
        </button>
      </div>
    </template>
  </section>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { listUsers } from '../utils/adminApi.js'
import { isoDate } from '../utils/isoDate.js'

const { t, n } = useI18n()
const PAGE_SIZE = 50

const items = ref([])
const total = ref(0)
const offset = ref(0)
const query = ref('')
const loading = ref(false)
const error = ref(false)
let searchTimer = null

const page = computed(() => Math.floor(offset.value / PAGE_SIZE) + 1)
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

function formatNumber(value) {
  return typeof value === 'number' ? n(value, 'integer') : '—'
}

async function load() {
  loading.value = true
  error.value = false
  try {
    const data = await listUsers({ q: query.value.trim(), offset: offset.value, limit: PAGE_SIZE })
    items.value = data.users
    total.value = data.total
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    offset.value = 0
    load()
  }, 300)
}

function prevPage() {
  offset.value = Math.max(0, offset.value - PAGE_SIZE)
  load()
}

function nextPage() {
  offset.value = offset.value + PAGE_SIZE
  load()
}

const formatDate = isoDate

onMounted(load)
onUnmounted(() => clearTimeout(searchTimer))
</script>

<style scoped>
.card {
  padding: 0 0 var(--space-6);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.card-head h2 {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  letter-spacing: -0.02em;
  font-weight: 700;
  color: var(--color-text);
}

.muted {
  max-width: 70ch;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  margin-bottom: var(--space-4);
}

.users-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.user-search {
  flex: 1;
  min-width: 180px;
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-text);
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.user-search:focus {
  outline: none;
  border-color: var(--color-accent);
}

.users-meta {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

/* Wide tables scroll inside their section on narrow screens. */
.table-scroll {
  overflow-x: auto;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: var(--space-4);
  font-size: var(--text-sm);
}

/* Column names as in the answer and report tables: sentence case on Cloud Ground. */
.users-table th {
  text-align: left;
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  background-color: var(--color-surface-container-low);
  border-bottom: 1px solid var(--color-border-strong);
}

.users-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
}

/* The table scrolls on a phone, so a name stays on one line instead of wrapping. */
.cell-name {
  white-space: nowrap;
}

.role-admin {
  font-weight: 600;
}

.cell-date {
  font-family: var(--font-mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.users-pager {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.pager-btn {
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text);
  background-color: var(--color-surface-container-high);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
}

.pager-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.pager-info {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
}

.error-box {
  margin-top: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-error);
  background-color: var(--color-error-bg);
  color: var(--color-error-accent);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.retry-btn {
  margin-left: var(--space-2);
  padding: 2px 10px;
  font-size: var(--text-xs);
  border: 1px solid currentColor;
  border-radius: var(--radius-md);
  background: transparent;
  color: inherit;
  cursor: pointer;
}
</style>
