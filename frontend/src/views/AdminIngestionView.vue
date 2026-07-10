<template>
  <div class="admin">
    <header class="topbar">
      <router-link class="brand" to="/app" title="Back to chat">
        <HelpingHandLogo :size="34" :radius="11" />
        <div class="brand-text">
          <h1 class="brand-title">Humanitaria</h1>
          <span class="brand-sub">Ingestion Admin</span>
        </div>
      </router-link>
      <div class="topbar-spacer"></div>
      <router-link class="back-link" to="/app"><ArrowLeft :size="16" /> Back to chat</router-link>
      <UserMenu />
    </header>

    <main class="content">
      <div v-if="forbidden" class="card error-card" role="alert">
        <h2>Access denied</h2>
        <p>You don't have permission to view this page.</p>
        <router-link class="primary-btn" to="/app">Back to chat</router-link>
      </div>

      <template v-else>
        <div v-if="actionError" class="action-error" role="alert">{{ actionError }}</div>

        <nav class="tabs" aria-label="Admin sections">
          <button
            type="button"
            :class="['tab-btn', { active: tab === 'ingestion' }]"
            @click="tab = 'ingestion'"
          >
            Ingestion
          </button>
          <button
            type="button"
            :class="['tab-btn', { active: tab === 'users' }]"
            @click="tab = 'users'"
          >
            Users
          </button>
        </nav>

        <template v-if="tab === 'ingestion'">
          <section class="card">
            <div class="card-head">
              <h2>Ingestion status</h2>
              <span :class="['pill', running ? 'pill-run' : 'pill-idle']">
                <span class="dot"></span>{{ running ? 'Running' : 'Idle' }}
              </span>
            </div>

            <p v-if="loading && !status" class="muted">Loading…</p>
            <dl v-else class="grid">
              <div>
                <dt>Last ingest</dt>
                <dd>{{ status?.last_ingest || '—' }}</dd>
              </div>
              <div>
                <dt>Next scheduled run</dt>
                <dd>{{ formatDateTime(status?.next_scheduled_run) }}</dd>
              </div>
              <div>
                <dt>Scheduler</dt>
                <dd>{{ status?.scheduler_active ? 'Active' : 'Inactive' }}</dd>
              </div>
              <div>
                <dt>Vectors (active namespace)</dt>
                <dd>
                  <span v-if="status?.vector_count_error" title="Pinecone unavailable"
                    >unavailable</span
                  >
                  <template v-else>
                    {{ formatNumber(status?.namespace_vectors) }}
                    <span class="dd-note"
                      >{{ namespaceLabel }} · {{ formatNumber(status?.total_vectors) }} in
                      index</span
                    >
                  </template>
                </dd>
              </div>
            </dl>
          </section>

          <section class="card">
            <div class="card-head"><h2>Run ingest</h2></div>
            <p class="muted">
              Fetches new ReliefWeb documents since the last run (incremental) and upserts them into
              Pinecone. A scheduled run uses the same path, so only one runs at a time.
            </p>
            <button class="primary-btn" :disabled="running || triggering" @click="onTrigger">
              <RefreshCw :size="16" :class="{ spin: running }" />
              {{ running ? 'Ingest in progress…' : 'Run ingest now' }}
            </button>

            <div v-if="run.last_error" class="error-box" role="alert">
              Last run failed: {{ run.last_error }}
            </div>

            <div v-if="lastStatsRows.length" class="run-summary">
              <h3>Last run</h3>
              <p class="muted run-meta">
                {{ run.source }} · started {{ formatDateTime(run.started_at) }}
                <template v-if="run.finished_at">
                  · finished {{ formatDateTime(run.finished_at) }}</template
                >
              </p>
              <table>
                <thead>
                  <tr>
                    <th>Endpoint</th>
                    <th>Total</th>
                    <th>OK</th>
                    <th>Failed</th>
                    <th>Skipped</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in lastStatsRows" :key="row.endpoint">
                    <td>{{ row.endpoint }}</td>
                    <td>{{ row.total }}</td>
                    <td>{{ row.succeeded }}</td>
                    <td>{{ row.failed }}</td>
                    <td>{{ row.skipped }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section class="card">
            <div class="card-head">
              <h2>Reports</h2>
              <span :class="['pill', docComputing ? 'pill-run' : 'pill-idle']">
                <span class="dot"></span>{{ docComputing ? 'Building' : 'Idle' }}
              </span>
            </div>
            <p class="muted">
              Indexed reports in the active namespace, newest first. The list builds automatically
              and refreshes after each ingest.
            </p>

            <div class="bd-actions">
              <input
                v-model="docQuery"
                class="doc-search"
                type="search"
                placeholder="Search title, source, country…"
                aria-label="Search reports"
                @input="onSearchInput"
              />
              <span v-if="docComputedAt" class="bd-meta">
                {{ formatNumber(docTotal) }} reports · updated {{ formatDateTime(docComputedAt) }}
              </span>
            </div>

            <div v-if="docError" class="error-box" role="alert">
              Last scan failed: {{ docError }}
            </div>

            <p v-if="docComputing && !docItems.length" class="muted bd-empty">
              Building the report list… this can take up to a minute.
            </p>
            <p v-else-if="!docItems.length" class="muted bd-empty">
              <template v-if="docQuery.trim()">No reports match “{{ docQuery }}”.</template>
              <template v-else>No reports found.</template>
            </p>

            <template v-if="docItems.length">
              <table class="doc-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Title</th>
                    <th>Source</th>
                    <th>Country</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in docItems" :key="row.doc_id">
                    <td class="doc-date">{{ formatDate(row.date) }}</td>
                    <td class="doc-title">
                      <a v-if="row.url" :href="row.url" target="_blank" rel="noopener">{{
                        row.title || '(untitled)'
                      }}</a>
                      <span v-else>{{ row.title || '(untitled)' }}</span>
                    </td>
                    <td>{{ row.source || '—' }}</td>
                    <td>{{ row.country || '—' }}</td>
                  </tr>
                </tbody>
              </table>

              <div class="doc-pager">
                <button class="pager-btn" :disabled="docOffset === 0" @click="prevPage">
                  Prev
                </button>
                <span class="pager-info">Page {{ docPage }} of {{ docPageCount }}</span>
                <button class="pager-btn" :disabled="docPage >= docPageCount" @click="nextPage">
                  Next
                </button>
              </div>
            </template>
          </section>
        </template>

        <AdminUsersPanel v-if="tab === 'users'" />
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ArrowLeft, RefreshCw } from 'lucide-vue-next'
import HelpingHandLogo from '../components/HelpingHandLogo.vue'
import UserMenu from '../components/UserMenu.vue'
import AdminUsersPanel from '../components/AdminUsersPanel.vue'
import { getIngestStatus, triggerIngest, getIngestDocuments } from '../utils/adminApi.js'

const tab = ref('ingestion')
const status = ref(null)
const loading = ref(true)
const triggering = ref(false)
const forbidden = ref(false)
const actionError = ref(null)
let pollTimer = null

const run = computed(() => status.value?.run || {})
const running = computed(() => run.value.running === true)
const lastStatsRows = computed(() =>
  Object.entries(run.value.last_stats || {}).map(([endpoint, s]) => ({ endpoint, ...s })),
)
const namespaceLabel = computed(() => {
  const ns = status.value?.namespace
  return ns ? `“${ns}” namespace` : 'default namespace'
})

// --- reports list (indexed documents, newest-first) ---
const docState = ref(null) // last /admin/ingest/documents response
const docOffset = ref(0)
const docLimit = ref(50)
const docQuery = ref('')
let docPollTimer = null
let searchTimer = null

const docItems = computed(() => docState.value?.items || [])
const docTotal = computed(() => docState.value?.total || 0)
const docComputing = computed(() => docState.value?.computing === true)
const docComputedAt = computed(() => docState.value?.computed_at || null)
const docError = computed(() => docState.value?.last_error || null)
const docPage = computed(() => Math.floor(docOffset.value / docLimit.value) + 1)
const docPageCount = computed(() => Math.max(1, Math.ceil(docTotal.value / docLimit.value)))

function formatNumber(n) {
  return typeof n === 'number' ? n.toLocaleString('en-US') : '—'
}

function formatDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d.getTime())
    ? '—'
    : d.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
}

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d.getTime()) ? iso : d.toLocaleDateString('en-GB', { dateStyle: 'medium' })
}

async function fetchStatus() {
  try {
    status.value = await getIngestStatus()
    forbidden.value = false
    actionError.value = null // a recovered poll clears any earlier transient error
    // Poll only while a run is active; stop once it goes idle.
    if (running.value) startPolling()
    else stopPolling()
  } catch (e) {
    if (e.status === 403) {
      forbidden.value = true
      stopPolling()
    } else actionError.value = 'Could not load ingestion status.'
  } finally {
    loading.value = false
  }
}

async function onTrigger() {
  triggering.value = true
  actionError.value = null
  try {
    await triggerIngest()
    await fetchStatus()
    startPolling()
  } catch (e) {
    if (e.status === 409) actionError.value = 'An ingest is already running.'
    else if (e.status === 403) {
      forbidden.value = true
      stopPolling()
    } else actionError.value = 'Could not start the ingest.'
  } finally {
    triggering.value = false
  }
}

function startPolling() {
  if (!pollTimer) pollTimer = setInterval(fetchStatus, 4000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function fetchDocuments() {
  try {
    docState.value = await getIngestDocuments({
      q: docQuery.value,
      offset: docOffset.value,
      limit: docLimit.value,
    })
    forbidden.value = false
    // Poll only while a scan is rebuilding the list; stop once it settles.
    if (docComputing.value) startDocPolling()
    else stopDocPolling()
  } catch (e) {
    if (e.status === 403) {
      forbidden.value = true
      stopDocPolling()
    } else actionError.value = 'Could not load the reports list.'
  }
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    docOffset.value = 0 // a new query starts from the first page
    fetchDocuments()
  }, 300)
}

function nextPage() {
  if (docPage.value >= docPageCount.value) return
  docOffset.value += docLimit.value
  fetchDocuments()
}

function prevPage() {
  if (docOffset.value === 0) return
  docOffset.value = Math.max(0, docOffset.value - docLimit.value)
  fetchDocuments()
}

function startDocPolling() {
  if (!docPollTimer) docPollTimer = setInterval(fetchDocuments, 4000)
}

function stopDocPolling() {
  if (docPollTimer) {
    clearInterval(docPollTimer)
    docPollTimer = null
  }
}

onMounted(() => {
  fetchStatus()
  fetchDocuments()
})
onUnmounted(() => {
  stopPolling()
  stopDocPolling()
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<style scoped>
.admin {
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
  background-color: var(--color-bg);
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  text-decoration: none;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.brand-title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-text);
}

.brand-sub {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
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
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
}

.back-link:hover {
  background-color: var(--color-surface-container-high);
  color: var(--color-text);
}

.content {
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.tabs {
  display: flex;
  gap: var(--space-1);
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.tab-btn {
  padding: var(--space-2) var(--space-4);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
}

.tab-btn.active {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}

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

.card h2 {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text);
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.grid dt {
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-muted);
  margin-bottom: var(--space-1);
}

.grid dd {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
}

.dd-note {
  display: block;
  margin-top: 2px;
  font-size: var(--text-xs);
  font-weight: 400;
  color: var(--color-muted);
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--radius-full);
}

.pill .dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: currentColor;
}

.pill-idle {
  color: var(--color-text-secondary);
  background-color: var(--color-surface-container-high);
}

.pill-run {
  color: var(--color-success);
  background-color: var(--color-accent-soft);
}

.pill-run .dot {
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

.muted {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  margin-bottom: var(--space-4);
}

.run-meta {
  margin-bottom: 0;
}

.primary-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-on-accent);
  background-color: var(--color-accent-container);
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  text-decoration: none;
  transition: background-color 0.2s;
}

.primary-btn:hover:not(:disabled) {
  background-color: var(--color-accent);
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-box,
.action-error {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-error);
  background-color: var(--color-error-bg);
  color: var(--color-error-accent);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.error-box {
  margin-top: var(--space-4);
}

.error-card {
  text-align: center;
}

.error-card h2 {
  margin-bottom: var(--space-2);
}

.error-card p {
  color: var(--color-text-secondary);
  margin-bottom: var(--space-4);
}

.run-summary {
  margin-top: var(--space-4);
}

.run-summary h3 {
  font-family: var(--font-display);
  font-size: var(--text-base);
  margin-bottom: var(--space-1);
  color: var(--color-text);
}

.run-summary table {
  width: 100%;
  border-collapse: collapse;
  margin-top: var(--space-3);
  font-size: var(--text-sm);
}

.run-summary th,
.run-summary td {
  text-align: left;
  padding: var(--space-2);
  border-bottom: 1px solid var(--color-border);
  font-variant-numeric: tabular-nums;
}

.run-summary th {
  color: var(--color-muted);
  font-weight: 600;
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.bd-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.bd-meta {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.bd-empty {
  margin-top: var(--space-4);
  margin-bottom: 0;
}

.doc-search {
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

.doc-search:focus {
  outline: none;
  border-color: var(--color-accent);
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: var(--space-4);
  font-size: var(--text-sm);
}

.doc-table th,
.doc-table td {
  text-align: left;
  padding: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.doc-table th {
  color: var(--color-muted);
  font-weight: 600;
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.doc-date {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}

.doc-title a {
  color: var(--color-accent);
  text-decoration: none;
}

.doc-title a:hover {
  text-decoration: underline;
}

.doc-pager {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.pager-info {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
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

@media (max-width: 640px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .brand-sub {
    display: none;
  }
}
</style>
