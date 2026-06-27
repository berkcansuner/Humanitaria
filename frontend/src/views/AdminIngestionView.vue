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
      <ThemeToggle />
    </header>

    <main class="content">
      <div v-if="forbidden" class="card error-card" role="alert">
        <h2>Access denied</h2>
        <p>You don't have permission to view this page.</p>
        <router-link class="primary-btn" to="/app">Back to chat</router-link>
      </div>

      <template v-else>
        <div v-if="actionError" class="action-error" role="alert">{{ actionError }}</div>

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
                <span v-if="status?.vector_count_error" title="Pinecone unavailable">unavailable</span>
                <template v-else>
                  {{ formatNumber(status?.namespace_vectors) }}
                  <span class="dd-note">{{ namespaceLabel }} · {{ formatNumber(status?.total_vectors) }} in index</span>
                </template>
              </dd>
            </div>
          </dl>
        </section>

        <section class="card">
          <div class="card-head"><h2>Run ingest</h2></div>
          <p class="muted">
            Fetches new ReliefWeb documents since the last run (incremental) and upserts
            them into Pinecone. A scheduled run uses the same path, so only one runs at a time.
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
              <template v-if="run.finished_at"> · finished {{ formatDateTime(run.finished_at) }}</template>
            </p>
            <table>
              <thead>
                <tr><th>Endpoint</th><th>Total</th><th>OK</th><th>Failed</th><th>Skipped</th></tr>
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
            <h2>Data breakdown</h2>
            <span :class="['pill', bdComputing ? 'pill-run' : 'pill-idle']">
              <span class="dot"></span>{{ bdComputing ? 'Scanning' : 'Idle' }}
            </span>
          </div>
          <p class="muted">
            Distinct reports in the active namespace, by source, date, country, theme and format.
            Full Pinecone scan (~3–5 min); the result is cached until you refresh.
          </p>

          <div class="bd-actions">
            <button class="primary-btn" :disabled="bdComputing || refreshingBd" @click="onRefreshBreakdown">
              <RefreshCw :size="16" :class="{ spin: bdComputing }" />
              {{ bdComputing ? 'Scanning namespace…' : 'Refresh breakdown' }}
            </button>
            <span v-if="bdData" class="bd-meta">
              {{ formatNumber(bdData.total_documents) }} reports · updated {{ formatDateTime(bdData.computed_at) }}
            </span>
            <span v-if="bdStale" class="stale-chip">stale — refresh to update</span>
          </div>

          <div v-if="breakdown?.last_error" class="error-box" role="alert">
            Last scan failed: {{ breakdown.last_error }}
          </div>

          <p v-if="!bdData && !bdComputing" class="muted bd-empty">
            No breakdown yet — click “Refresh breakdown” to scan the index.
          </p>

          <template v-if="bdData">
            <div class="bd-block">
              <h3>By source</h3>
              <div v-for="row in bdData.by_source" :key="'s-' + row.key" class="bar-row">
                <span class="bar-label" :title="row.key">{{ row.key }}</span>
                <span class="bar-track"><span class="bar-fill" :style="{ width: barWidth(row.count, bdSourceMax) }"></span></span>
                <span class="bar-count">{{ formatNumber(row.count) }}</span>
              </div>
            </div>

            <div class="bd-block">
              <h3>By country</h3>
              <div v-for="row in bdData.by_country" :key="'c-' + row.key" class="bar-row">
                <span class="bar-label" :title="row.key">{{ row.key }}</span>
                <span class="bar-track"><span class="bar-fill" :style="{ width: barWidth(row.count, bdCountryMax) }"></span></span>
                <span class="bar-count">{{ formatNumber(row.count) }}</span>
              </div>
            </div>

            <div class="bd-block">
              <h3>By month</h3>
              <div class="histogram">
                <span
                  v-for="b in bdData.by_month"
                  :key="'m-' + b.month"
                  class="hist-col"
                  :style="{ height: barWidth(b.count, bdMonthMax) }"
                  :title="`${b.month}: ${b.count}`"
                ></span>
              </div>
              <div v-if="bdData.by_month.length" class="hist-axis">
                <span>{{ bdData.by_month[0].month }}</span>
                <span>{{ bdData.by_month[bdData.by_month.length - 1].month }}</span>
              </div>
            </div>

            <div class="bd-tables">
              <div class="bd-block">
                <h3>By theme</h3>
                <table>
                  <tbody>
                    <tr v-for="row in bdData.by_theme" :key="'t-' + row.key">
                      <td>{{ row.key }}</td><td>{{ formatNumber(row.count) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="bd-block">
                <h3>By format</h3>
                <table>
                  <tbody>
                    <tr v-for="row in bdData.by_format" :key="'f-' + row.key">
                      <td>{{ row.key }}</td><td>{{ formatNumber(row.count) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="bd-block">
                <h3>By year</h3>
                <table>
                  <tbody>
                    <tr v-for="row in bdData.by_year" :key="'y-' + row.year">
                      <td>{{ row.year }}</td><td>{{ formatNumber(row.count) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </template>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ArrowLeft, RefreshCw } from 'lucide-vue-next'
import HelpingHandLogo from '../components/HelpingHandLogo.vue'
import ThemeToggle from '../components/ThemeToggle.vue'
import { getIngestStatus, triggerIngest, getIngestBreakdown, refreshIngestBreakdown } from '../utils/adminApi.js'

const status = ref(null)
const loading = ref(true)
const triggering = ref(false)
const forbidden = ref(false)
const actionError = ref(null)
let pollTimer = null

const run = computed(() => status.value?.run || {})
const running = computed(() => run.value.running === true)
const lastStatsRows = computed(() =>
  Object.entries(run.value.last_stats || {}).map(([endpoint, s]) => ({ endpoint, ...s }))
)
const namespaceLabel = computed(() => {
  const ns = status.value?.namespace
  return ns ? `“${ns}” namespace` : 'default namespace'
})

// --- breakdown (indexed-data analytics) ---
const breakdown = ref(null)
const refreshingBd = ref(false)
let bdPollTimer = null

const bdData = computed(() => breakdown.value?.data || null)
const bdComputing = computed(() => breakdown.value?.computing === true)
const bdStale = computed(() => breakdown.value?.stale === true)
const bdSourceMax = computed(() => Math.max(1, ...(bdData.value?.by_source || []).map((r) => r.count)))
const bdCountryMax = computed(() => Math.max(1, ...(bdData.value?.by_country || []).map((r) => r.count)))
const bdMonthMax = computed(() => Math.max(1, ...(bdData.value?.by_month || []).map((r) => r.count)))

function barWidth(count, max) {
  return max > 0 ? `${(count / max) * 100}%` : '0%'
}

function formatNumber(n) {
  return typeof n === 'number' ? n.toLocaleString('en-US') : '—'
}

function formatDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d.getTime()) ? '—' : d.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
}

async function fetchStatus() {
  try {
    status.value = await getIngestStatus()
    forbidden.value = false
    actionError.value = null   // a recovered poll clears any earlier transient error
    // Poll only while a run is active; stop once it goes idle.
    if (running.value) startPolling()
    else stopPolling()
  } catch (e) {
    if (e.status === 403) { forbidden.value = true; stopPolling() }
    else actionError.value = 'Could not load ingestion status.'
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
    else if (e.status === 403) { forbidden.value = true; stopPolling() }
    else actionError.value = 'Could not start the ingest.'
  } finally {
    triggering.value = false
  }
}

function startPolling() {
  if (!pollTimer) pollTimer = setInterval(fetchStatus, 4000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function fetchBreakdown() {
  try {
    breakdown.value = await getIngestBreakdown()
    forbidden.value = false
    if (bdComputing.value) startBdPolling()
    else stopBdPolling()
  } catch (e) {
    if (e.status === 403) { forbidden.value = true; stopBdPolling() }
    else actionError.value = 'Could not load the data breakdown.'
  }
}

async function onRefreshBreakdown() {
  refreshingBd.value = true
  actionError.value = null
  try {
    await refreshIngestBreakdown()
    await fetchBreakdown()
    startBdPolling()
  } catch (e) {
    if (e.status === 409) await fetchBreakdown()        // a scan is already running — just sync
    else if (e.status === 403) { forbidden.value = true; stopBdPolling() }
    else actionError.value = 'Could not start the breakdown scan.'
  } finally {
    refreshingBd.value = false
  }
}

function startBdPolling() {
  if (!bdPollTimer) bdPollTimer = setInterval(fetchBreakdown, 4000)
}

function stopBdPolling() {
  if (bdPollTimer) { clearInterval(bdPollTimer); bdPollTimer = null }
}

onMounted(() => { fetchStatus(); fetchBreakdown() })
onUnmounted(() => { stopPolling(); stopBdPolling() })
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
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
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
  to { transform: rotate(360deg); }
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

.stale-chip {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-error-accent);
  background-color: var(--color-error-bg);
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.bd-empty {
  margin-top: var(--space-4);
  margin-bottom: 0;
}

.bd-block {
  margin-top: var(--space-5);
}

.bd-block h3 {
  font-family: var(--font-display);
  font-size: var(--text-base);
  color: var(--color-text);
  margin-bottom: var(--space-3);
}

.bar-row {
  display: grid;
  grid-template-columns: 140px 1fr 56px;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.bar-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bar-track {
  height: 10px;
  background-color: var(--color-surface-container-high);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.bar-fill {
  display: block;
  height: 100%;
  background-color: var(--color-accent);
  border-radius: var(--radius-full);
}

.bar-count {
  font-size: var(--text-sm);
  font-variant-numeric: tabular-nums;
  text-align: right;
  color: var(--color-text);
}

.histogram {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 80px;
  padding: var(--space-2) 0;
}

.hist-col {
  flex: 1;
  min-width: 2px;
  min-height: 1px;
  background-color: var(--color-accent);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}

.hist-axis {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-xs);
  color: var(--color-muted);
  font-variant-numeric: tabular-nums;
}

.bd-tables {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-5);
}

.bd-tables table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.bd-tables td {
  padding: var(--space-1) var(--space-2);
  border-bottom: 1px solid var(--color-border);
  font-variant-numeric: tabular-nums;
}

.bd-tables td:last-child {
  text-align: right;
  color: var(--color-text-secondary);
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
