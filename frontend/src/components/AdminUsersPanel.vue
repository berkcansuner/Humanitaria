<template>
  <section class="card">
    <div class="card-head"><h2>Users</h2></div>
    <p class="muted">Registered accounts, newest first. Read-only.</p>

    <div class="users-actions">
      <input
        v-model="query"
        class="user-search"
        type="search"
        placeholder="Search email or name…"
        aria-label="Search users"
        @input="onSearchInput"
      />
      <span v-if="!loading" class="users-meta">{{ total }} users</span>
    </div>

    <div v-if="error" class="error-box" role="alert">
      Could not load users.
      <button class="retry-btn" type="button" @click="load">Retry</button>
    </div>

    <p v-if="loading && !items.length" class="muted">Loading…</p>
    <p v-else-if="!loading && !items.length" class="muted">
      <template v-if="query.trim()">No users match “{{ query }}”.</template>
      <template v-else>No users found.</template>
    </p>

    <template v-if="items.length">
      <table class="users-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Provider</th>
            <th>Admin</th>
            <th>Joined</th>
            <th>Last login</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in items" :key="u.id">
            <td>{{ u.name || '—' }}</td>
            <td>{{ u.email }}</td>
            <td>{{ u.auth_provider === 'google' ? 'Google' : 'Password' }}</td>
            <td>
              <span v-if="u.is_admin" class="admin-badge">admin</span>
              <span v-else>—</span>
            </td>
            <td>{{ formatDate(u.created_at) }}</td>
            <td>{{ u.last_login ? formatDate(u.last_login) : '—' }}</td>
          </tr>
        </tbody>
      </table>

      <div class="users-pager">
        <button class="pager-btn" :disabled="offset === 0" @click="prevPage">Prev</button>
        <span class="pager-info">Page {{ page }} of {{ pageCount }}</span>
        <button class="pager-btn" :disabled="page >= pageCount" @click="nextPage">Next</button>
      </div>
    </template>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { listUsers } from '../utils/adminApi.js'

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

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d) ? iso : d.toLocaleDateString()
}

onMounted(load)
</script>

<style scoped>
.card {
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.card-head h2 {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text);
}

.muted {
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

.users-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: var(--space-4);
  font-size: var(--text-sm);
}

.users-table th {
  text-align: left;
  padding: var(--space-2);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-muted);
  border-bottom: 1px solid var(--color-border);
}

.users-table td {
  padding: var(--space-2);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
}

.admin-badge {
  display: inline-block;
  padding: 4px 10px;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-on-accent);
  background-color: var(--color-accent-container);
  border-radius: var(--radius-full);
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
