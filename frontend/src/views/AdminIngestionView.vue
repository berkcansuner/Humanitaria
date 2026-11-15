<template>
  <div class="admin">
    <AppTopbar context="Admin" />

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
            :aria-current="tab === 'ingestion' ? 'true' : undefined"
            @click="tab = 'ingestion'"
          >
            Ingestion
          </button>
          <button
            type="button"
            :class="['tab-btn', { active: tab === 'users' }]"
            :aria-current="tab === 'users' ? 'true' : undefined"
            @click="tab = 'users'"
          >
            Users
          </button>
        </nav>

        <template v-if="tab === 'ingestion'">
          <section class="card">
            <div class="card-head">
              <h2>Ingestion status</h2>
              <span :class="['state', { 'state-on': running }]">
                <span class="dot" aria-hidden="true"></span>{{ running ? 'Running' : 'Idle' }}
              </span>
            </div>

            <p v-if="loading && !status" class="muted">Loading…</p>
            <dl v-else class="grid">
              <div>
                <dt>Last ingest</dt>
                <dd>{{ status?.last_ingest || '—' }}</dd>
              </div>
              <!-- Production runs from the Cloudflare cron Worker (cloudflare-cron/), so
                   the in-app scheduler is off there by design; say how runs happen
                   instead of showing "Inactive" as if something were broken. -->
              <div v-if="status?.scheduler_active">
                <dt>Next scheduled run</dt>
                <dd>{{ formatDateTime(status?.next_scheduled_run) }}</dd>
              </div>
              <div v-else>
                <dt>Schedule</dt>
                <dd>
                  Nightly, 03:00 UTC
                  <span class="dd-note">via the Cloudflare cron</span>
                </dd>
              </div>
              <div>
                <dt>Indexed chunks</dt>
                <dd>
                  <span v-if="status?.vector_count_error" title="Database unavailable"
                    >unavailable</span
                  >
                  <template v-else>
                    {{ formatNumber(status?.chunk_count) }}
                    <span class="dd-note"
                      >{{ formatNumber(status?.document_count) }} documents</span
                    >
                  </template>
                </dd>
              </div>
            </dl>
          </section>

          <section class="card">
            <div class="card-head"><h2>Run ingest</h2></div>
            <p class="muted">
              Fetches ReliefWeb documents published since the last run and adds them to the search
              index. The nightly run uses the same path, so only one runs at a time.
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
              <span v-if="docComputing" class="state state-on">
                <span class="dot" aria-hidden="true"></span>Building
              </span>
            </div>
            <p class="muted">
              Indexed reports, newest first. The list updates as each ingest writes new documents.
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
              <div class="table-scroll">
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
              </div>

              <div v-if="docPageCount > 1" class="doc-pager">
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
import { RefreshCw } from 'lucide-vue-next'
import AppTopbar from '../components/AppTopbar.vue'
import AdminUsersPanel from '../components/AdminUsersPanel.vue'
import { getIngestStatus, triggerIngest, getIngestDocuments } from '../utils/adminApi.js'
import { isoDate, isoDateTime } from '../utils/isoDate.js'

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

const formatDateTime = isoDateTime

const formatDate = isoDate

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

.content {
  width: 100%;
  max-width: 1120px;
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

/* Quiet Archive: sections are hairline-separated bands, not shadowed cards. */
.card {
  padding: var(--space-5) 0 var(--space-6);
  border-top: 1px solid var(--color-border);
}

.tabs + .card {
  border-top: none;
  padding-top: 0;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.card h2 {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-text);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4) var(--space-6);
}

.grid dt {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-1);
}

.grid dd {
  font-family: var(--font-mono);
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
}

.dd-note {
  display: block;
  margin-top: 2px;
  font-family: var(--font-body);
  font-size: var(--text-xs);
  font-weight: 400;
  color: var(--color-muted);
}

/* Status as text with a small dot, not a pill; green only while work runs. */
.state {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.state .dot {
  width: 7px;
  height: 7px;
  border-radius: var(--radius-full);
  background-color: var(--color-muted);
}

.state-on {
  color: var(--color-accent);
  font-weight: 600;
}

.state-on .dot {
  background-color: var(--color-accent);
  animation: pulse 1.2s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  .state-on .dot {
    animation: none;
  }
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
  max-width: 70ch;
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
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-text-secondary);
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

/* Wide tables scroll inside their section on narrow screens. */
.table-scroll {
  overflow-x: auto;
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
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-text-secondary);
}

.doc-date {
  font-family: var(--font-mono);
  font-size: 12.5px;
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
}
</style>
