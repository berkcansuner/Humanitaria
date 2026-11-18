<template>
  <div class="admin">
    <AppTopbar :context="t('titles.admin')" />

    <main class="content">
      <div v-if="forbidden" class="card error-card" role="alert">
        <h2>{{ t('admin.forbidden.title') }}</h2>
        <p>{{ t('admin.forbidden.text') }}</p>
        <router-link class="primary-btn" to="/app">{{ t('admin.forbidden.back') }}</router-link>
      </div>

      <template v-else>
        <div v-if="actionError" class="action-error" role="alert">{{ actionError }}</div>

        <nav class="tabs" :aria-label="t('admin.tabsLabel')">
          <button
            type="button"
            :class="['tab-btn', { active: tab === 'ingestion' }]"
            :aria-current="tab === 'ingestion' ? 'true' : undefined"
            @click="tab = 'ingestion'"
          >
            {{ t('admin.tabs.ingestion') }}
          </button>
          <button
            type="button"
            :class="['tab-btn', { active: tab === 'users' }]"
            :aria-current="tab === 'users' ? 'true' : undefined"
            @click="tab = 'users'"
          >
            {{ t('admin.tabs.users') }}
          </button>
        </nav>

        <template v-if="tab === 'ingestion'">
          <section class="card">
            <div class="card-head">
              <h2>{{ t('admin.status.title') }}</h2>
              <span :class="['state', { 'state-on': running }]">
                <span class="dot" aria-hidden="true"></span
                >{{ running ? t('admin.status.running') : t('admin.status.idle') }}
              </span>
            </div>

            <p v-if="loading && !status" class="muted">{{ t('common.loading') }}</p>
            <dl v-else class="grid">
              <div>
                <dt>{{ t('admin.status.lastIngest') }}</dt>
                <dd>{{ status?.last_ingest || '—' }}</dd>
              </div>
              <!-- Production runs from GitHub Actions (.github/workflows/nightly-ingest.yml),
                   so the in-app scheduler is off there by design; say how runs happen
                   instead of showing "Inactive" as if something were broken. -->
              <div v-if="status?.scheduler_active">
                <dt>{{ t('admin.status.nextRun') }}</dt>
                <dd>{{ formatDateTime(status?.next_scheduled_run) }}</dd>
              </div>
              <div v-else>
                <dt>{{ t('admin.status.schedule') }}</dt>
                <dd>
                  {{ t('admin.status.scheduleValue') }}
                  <span class="dd-note">{{ t('admin.status.scheduleNote') }}</span>
                </dd>
              </div>
              <div>
                <dt>{{ t('admin.status.chunks') }}</dt>
                <dd>
                  <span
                    v-if="status?.vector_count_error"
                    :title="t('admin.status.dbUnavailable')"
                    >{{ t('admin.status.unavailable') }}</span
                  >
                  <template v-else>
                    {{ formatNumber(status?.chunk_count) }}
                    <span class="dd-note">{{
                      t(
                        'admin.status.documents',
                        { n: formatNumber(status?.document_count) },
                        status?.document_count ?? 0,
                      )
                    }}</span>
                  </template>
                </dd>
              </div>
            </dl>
          </section>

          <section class="card">
            <div class="card-head">
              <h2>{{ t('admin.run.title') }}</h2>
            </div>
            <p class="muted">{{ t('admin.run.text') }}</p>
            <button class="primary-btn" :disabled="running || triggering" @click="onTrigger">
              <RefreshCw :size="16" :class="{ spin: running }" />
              {{ running ? t('admin.run.inProgress') : t('admin.run.button') }}
            </button>

            <div v-if="run.last_error" class="error-box" role="alert">
              {{ t('admin.run.lastFailed', { error: run.last_error }) }}
            </div>

            <div v-if="lastStatsRows.length" class="run-summary">
              <h3>{{ t('admin.run.lastRun') }}</h3>
              <p class="muted run-meta">
                {{
                  run.finished_at
                    ? t('admin.run.metaFinished', {
                        source: run.source,
                        start: formatDateTime(run.started_at),
                        end: formatDateTime(run.finished_at),
                      })
                    : t('admin.run.meta', {
                        source: run.source,
                        start: formatDateTime(run.started_at),
                      })
                }}
              </p>
              <table>
                <thead>
                  <tr>
                    <th>{{ t('admin.run.endpoint') }}</th>
                    <th>{{ t('admin.run.total') }}</th>
                    <th>{{ t('admin.run.ok') }}</th>
                    <th>{{ t('admin.run.failed') }}</th>
                    <th>{{ t('admin.run.skipped') }}</th>
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
              <h2>{{ t('admin.reports.title') }}</h2>
              <span v-if="docComputing" class="state state-on">
                <span class="dot" aria-hidden="true"></span>{{ t('admin.reports.building') }}
              </span>
            </div>
            <p class="muted">{{ t('admin.reports.text') }}</p>

            <div class="bd-actions">
              <input
                v-model="docQuery"
                class="doc-search"
                type="search"
                :placeholder="t('admin.reports.placeholder')"
                :aria-label="t('admin.reports.searchLabel')"
                @input="onSearchInput"
              />
              <span v-if="docComputedAt" class="bd-meta">
                {{
                  t(
                    'admin.reports.count',
                    { n: formatNumber(docTotal), time: formatDateTime(docComputedAt) },
                    docTotal,
                  )
                }}
              </span>
            </div>

            <div v-if="docError" class="error-box" role="alert">
              {{ t('admin.reports.scanFailed', { error: docError }) }}
            </div>

            <p v-if="docComputing && !docItems.length" class="muted bd-empty">
              {{ t('admin.reports.buildingList') }}
            </p>
            <p v-else-if="!docItems.length" class="muted bd-empty">
              <template v-if="docQuery.trim()">{{
                t('admin.reports.noMatch', { q: docQuery })
              }}</template>
              <template v-else>{{ t('admin.reports.none') }}</template>
            </p>

            <template v-if="docItems.length">
              <div class="table-scroll">
                <table class="doc-table">
                  <thead>
                    <tr>
                      <th>{{ t('admin.reports.date') }}</th>
                      <th>{{ t('admin.reports.titleCol') }}</th>
                      <th>{{ t('admin.reports.source') }}</th>
                      <th>{{ t('admin.reports.country') }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in docItems" :key="row.doc_id">
                      <td class="doc-date">{{ formatDate(row.date) }}</td>
                      <td class="doc-title">
                        <a v-if="row.url" :href="row.url" target="_blank" rel="noopener">{{
                          row.title || t('admin.reports.untitled')
                        }}</a>
                        <span v-else>{{ row.title || t('admin.reports.untitled') }}</span>
                      </td>
                      <td>{{ row.source || '—' }}</td>
                      <td>{{ row.country || '—' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div v-if="docPageCount > 1" class="doc-pager">
                <button class="pager-btn" :disabled="docOffset === 0" @click="prevPage">
                  {{ t('admin.pager.prev') }}
                </button>
                <span class="pager-info">{{
                  t('admin.pager.page', { page: docPage, total: docPageCount })
                }}</span>
                <button class="pager-btn" :disabled="docPage >= docPageCount" @click="nextPage">
                  {{ t('admin.pager.next') }}
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
import { useI18n } from 'vue-i18n'
import { RefreshCw } from 'lucide-vue-next'
import AppTopbar from '../components/AppTopbar.vue'
import AdminUsersPanel from '../components/AdminUsersPanel.vue'
import { getIngestStatus, triggerIngest, getIngestDocuments } from '../utils/adminApi.js'
import { isoDate, isoDateTime } from '../utils/isoDate.js'
import { errorMessage } from '../utils/errorMessage.js'

const { t, n } = useI18n()

const tab = ref('ingestion')
const status = ref(null)
const loading = ref(true)
const triggering = ref(false)
const forbidden = ref(false)
// The failed request (and which action it was), translated at render so it follows a
// language switch.
const actionProblem = ref(null)
const actionError = computed(() => {
  const p = actionProblem.value
  return p ? errorMessage(p.err, t, p.fallback) : null
})
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

function formatNumber(value) {
  return typeof value === 'number' ? n(value, 'integer') : '—'
}

const formatDateTime = isoDateTime

const formatDate = isoDate

async function fetchStatus() {
  try {
    status.value = await getIngestStatus()
    forbidden.value = false
    actionProblem.value = null // a recovered poll clears any earlier transient error
    // Poll only while a run is active; stop once it goes idle.
    if (running.value) startPolling()
    else stopPolling()
  } catch (e) {
    if (e.status === 403) {
      forbidden.value = true
      stopPolling()
    } else actionProblem.value = { err: e, fallback: 'admin.errors.status' }
  } finally {
    loading.value = false
  }
}

async function onTrigger() {
  triggering.value = true
  actionProblem.value = null
  try {
    await triggerIngest()
    await fetchStatus()
    startPolling()
  } catch (e) {
    if (e.status === 403) {
      forbidden.value = true
      stopPolling()
    } else actionProblem.value = { err: e, fallback: 'admin.errors.start' }
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
    } else actionProblem.value = { err: e, fallback: 'admin.errors.reports' }
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
  font-family: var(--font-body);
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
  font-family: var(--font-body);
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
  font-family: var(--font-body);
  font-weight: 500;
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-text-secondary);
}

.doc-date {
  font-family: var(--font-body);
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

/* Turkish column headings are longer; let the run table scroll inside its section
   on a phone instead of widening the page. */
html[lang='tr'] .run-summary {
  overflow-x: auto;
}
</style>
