<template>
  <div class="reports-app">
    <AppTopbar context="M&amp;E Reports" />

    <div class="reports-body">
      <aside class="reports-aside">
        <form class="report-form" @submit.prevent="generate">
          <h2 class="form-title">New report</h2>

          <label class="field">
            <span>Report type</span>
            <select v-model="form.report_type" :disabled="generating">
              <option v-for="t in REPORT_TYPES" :key="t.value" :value="t.value">
                {{ t.label }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>Country</span>
            <select v-model="form.country" required :disabled="generating">
              <option value="" disabled>Select a country…</option>
              <option v-for="c in countries" :key="c" :value="c">{{ c }}</option>
            </select>
          </label>

          <label class="field">
            <span>Sector</span>
            <select v-model="form.theme" :disabled="generating">
              <option value="">All sectors</option>
              <option v-for="t in themes" :key="t" :value="t">{{ t }}</option>
            </select>
          </label>

          <div class="field-row">
            <label class="field">
              <span>From</span>
              <input
                v-model="form.date_from"
                type="date"
                :min="minDate"
                :max="form.date_to || maxDate"
                :disabled="generating"
              />
            </label>
            <label class="field">
              <span>To</span>
              <input
                v-model="form.date_to"
                type="date"
                :min="form.date_from || minDate"
                :max="maxDate"
                :disabled="generating"
              />
            </label>
          </div>

          <label class="field">
            <span>Language</span>
            <select v-model="form.language" :disabled="generating">
              <option value="en">English</option>
              <option value="tr">Türkçe</option>
            </select>
          </label>

          <button type="submit" class="generate-btn" :disabled="!form.country || generating">
            <Loader2 v-if="generating" :size="16" class="spin" />
            <FileText v-else :size="16" />
            {{ generating ? 'Generating…' : 'Generate report' }}
          </button>

          <p v-if="optionsError" class="form-hint">Could not load options. Try refreshing.</p>
          <p v-else-if="!countries.length" class="form-hint">Preparing the country list…</p>
          <p v-else-if="!form.country && !generating" class="form-hint">
            Choose a country to generate a report.
          </p>
        </form>

        <div class="saved">
          <h3 class="saved-title-h">Saved reports</h3>
          <template v-if="loadingList && !reports.length">
            <span v-for="n in 4" :key="'sk-' + n" class="skeleton saved-skel"></span>
          </template>
          <ul v-else-if="visibleReports.length" class="saved-list">
            <li
              v-for="r in visibleReports"
              :key="r.id"
              :class="[
                'saved-item',
                { active: current && current.id === r.id, opening: openingId === r.id },
              ]"
              :aria-busy="openingId === r.id ? 'true' : undefined"
            >
              <button type="button" class="saved-open" :title="r.title" @click="openReport(r.id)">
                <span class="saved-name">{{ savedName(r) }}</span>
                <span class="saved-meta"
                  >{{ savedType(r)
                  }}<template v-if="savedPeriod(r)">
                    · <span class="saved-period">{{ savedPeriod(r) }}</span></template
                  ></span
                >
              </button>
              <button
                type="button"
                class="saved-del"
                aria-label="Delete report"
                @click.stop="onDelete(r.id)"
              >
                <Trash2 :size="13" />
              </button>
            </li>
          </ul>
          <p v-else class="form-hint">No saved reports yet.</p>
        </div>
      </aside>

      <main ref="viewer" class="report-main" @click="onCiteClick">
        <!-- One reading column: every block shares its 70ch measure (set at body size),
             so the Sources line and the header align with the text. -->
        <!-- Opening a saved report: a skeleton instead of a silent wait. -->
        <div v-if="openingId" class="report-column" aria-busy="true">
          <div class="report-loading">
            <span class="skeleton skel-line title"></span>
            <span class="skeleton skel-line"></span>
            <span class="skeleton skel-line"></span>
            <span class="skeleton skel-line short"></span>
          </div>
        </div>
        <div v-else-if="current" class="report-column">
          <img v-if="current.cover_image" class="cover-img" :src="current.cover_image" alt="" />
          <p v-if="current.imagesStatus" class="images-status">{{ current.imagesStatus }}</p>
          <header v-if="titleParts.heading || current.id" class="report-head">
            <div class="report-head-text">
              <h2 v-if="titleParts.heading" class="report-title-h">{{ titleParts.heading }}</h2>
              <p v-if="metaParts.length" class="report-meta">
                <span v-for="(part, i) in metaParts" :key="i" class="meta-part"
                  >{{ i ? '· ' : '' }}{{ part }}</span
                >
              </p>
            </div>
            <div v-if="current.id" class="report-actions">
              <button type="button" class="pdf-btn" @click="copyReport">
                <Check v-if="reportCopied" :size="15" />
                <Copy v-else :size="15" />
                {{ reportCopied ? 'Copied' : 'Copy with sources' }}
              </button>
              <button type="button" class="pdf-btn" :disabled="pdfLoading" @click="downloadPdf">
                <Loader2 v-if="pdfLoading" :size="15" class="spin" />
                <FileDown v-else :size="15" />
                {{ pdfLoading ? 'Preparing…' : 'Download PDF' }}
              </button>
            </div>
          </header>
          <p v-if="pdfError" class="pdf-error">{{ pdfError }}</p>
          <div v-if="!current.content && generating" class="report-loading">
            <span class="skeleton skel-line"></span>
            <span class="skeleton skel-line"></span>
            <span class="skeleton skel-line short"></span>
          </div>
          <article
            v-else
            class="report-content"
            v-html="
              injectSectionImages(
                renderMarkdown(current.content, current.sources),
                current.section_images,
              )
            "
          ></article>
          <div v-if="genError" class="error-banner"><AlertCircle :size="16" /> {{ genError }}</div>
          <SourceList v-if="current.sources" :sources="current.sources" />
        </div>
        <div v-else class="report-empty">
          <FileText :size="40" />
          <p>Generate a situation report, or open a saved one.</p>
        </div>
      </main>
    </div>
    <CitePreview :root="viewer" />
    <UndoToast
      :message="toastMessage"
      :kind="pendingDelete ? 'undo' : 'error'"
      :action-label="pendingDelete ? 'Undo' : ''"
      :focus-action="!!pendingDelete"
      :focus-key="pendingDelete ? pendingDelete.id : null"
      @action="undoDelete"
      @dismiss="notice = ''"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { FileText, Trash2, Loader2, AlertCircle, FileDown, Copy, Check } from 'lucide-vue-next'
import AppTopbar from '../components/AppTopbar.vue'
import SourceList from '../components/SourceList.vue'
import UndoToast from '../components/UndoToast.vue'
import CitePreview from '../components/CitePreview.vue'
import { useUndoableDelete } from '../utils/undoableDelete.js'
import { renderMarkdown } from '../utils/renderMarkdown.js'
import { injectSectionImages } from '../utils/reportImages.js'
import { revealSource, returnToCite } from '../utils/sources.js'
import { parseSSE } from '../utils/parseSSE.js'
import { getReportOptions, listReports, getReport, deleteReport } from '../utils/reportsApi.js'
import { REPORT_TYPES, reportTypeBadge } from '../utils/reportTypes.js'
import { splitReportTitle } from '../utils/reportTitle.js'
import { copyWithSources } from '../utils/citationCopy.js'
import { minReportDate, maxReportDate } from '../utils/reportDateBounds.js'
import { handleSessionExpired } from '../utils/authStore.js'

// Prod retains ~1 year of data; clamp the date pickers to [one year ago, today]
// so a user can't pick a window with no indexed reports (or a future date).
const minDate = computed(() => minReportDate(new Date(), form.value.report_type))
const maxDate = computed(() => maxReportDate())

const countries = ref([])
const themes = ref([])
const optionsError = ref(false)

const reports = ref([])
const loadingList = ref(false)
const openingId = ref(null) // saved report being fetched for the viewer

const form = ref({
  report_type: 'situation',
  country: '',
  theme: '',
  date_from: '',
  date_to: '',
  language: 'en',
})

const current = ref(null) // { id, title, content, sources }
const generating = ref(false)
const genError = ref('')
const viewer = ref(null)
const controller = ref(null)

const pdfLoading = ref(false)
const pdfError = ref('')

const _iso = (d) => d.toISOString().slice(0, 10)

function setDefaultDates() {
  const to = new Date()
  const from = new Date()
  from.setMonth(from.getMonth() - 3)
  form.value.date_from = _iso(from)
  form.value.date_to = _iso(to)
}

// Titles carry "[Type —] Country · Sector · period"; the country leads, the rest
// moves to a mono meta line (type as text, not a pill).
function typeLabel(type) {
  return (REPORT_TYPES.find((t) => t.value === type) || REPORT_TYPES[0]).label
}

function savedName(r) {
  const { heading, sector } = splitReportTitle(r.title)
  return sector && sector !== 'All sectors' ? `${heading} · ${sector}` : heading
}

function savedType(r) {
  return reportTypeBadge(r.report_type) || 'Situation'
}

function savedPeriod(r) {
  return splitReportTitle(r.title).period
}

// Copy the report text with its numbered Sources list (the PDF stays separate).
const reportCopied = ref(false)
let copiedTimer = null
async function copyReport() {
  if (!current.value) return
  const ok = await copyWithSources(current.value.content, current.value.sources)
  if (!ok) {
    showNotice('Could not copy the report. Your browser blocked clipboard access.')
    return
  }
  reportCopied.value = true
  clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => (reportCopied.value = false), 1500)
}

const titleParts = computed(() => splitReportTitle(current.value && current.value.title))
// Type · sector · period, each kept whole: the line only wraps between parts,
// and a part carries its leading "·" so no separator is left at a line end.
const metaParts = computed(() => {
  if (!current.value || !current.value.title) return []
  const { sector, period } = titleParts.value
  return [typeLabel(current.value.report_type), sector, period].filter(Boolean)
})

onMounted(async () => {
  setDefaultDates()
  try {
    const opts = await getReportOptions()
    countries.value = opts.countries || []
    themes.value = opts.themes || []
  } catch (e) {
    optionsError.value = true
  }
  await loadList()
})

async function loadList() {
  loadingList.value = true
  try {
    reports.value = (await listReports()).reports || []
  } catch (e) {
    console.error('Failed to load reports:', e)
    showNotice('Could not load your saved reports. Try refreshing the page.')
  } finally {
    loadingList.value = false
  }
}

async function openReport(id) {
  if (generating.value) return
  openingId.value = id
  try {
    const rep = await getReport(id)
    current.value = {
      id: rep.id,
      title: rep.title,
      content: rep.content,
      sources: rep.sources,
      report_type: rep.report_type,
      cover_image: rep.cover_image,
      section_images: rep.section_images,
    }
    genError.value = ''
    nextTick(() => {
      if (viewer.value) viewer.value.scrollTop = 0
    })
  } catch (e) {
    console.error('Failed to open report:', e)
    showNotice('Could not open the report. Try again.')
  } finally {
    if (openingId.value === id) openingId.value = null
  }
}

// Errors for list actions, shown in the same toast as Undo (they used to reach
// only the console). Cleared after a few seconds or by the dismiss button.
const notice = ref('')
let noticeTimer = null
function showNotice(message) {
  notice.value = message
  clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => (notice.value = ''), 6000)
}

// A saved report is the user's deliverable: delete hides it at once and offers
// Undo for 8 s before the DELETE is sent (see useUndoableDelete).
const {
  hiddenIds,
  pending: pendingDelete,
  remove: removeReport,
  undo: undoDelete,
  flush: flushDelete,
} = useUndoableDelete({
  commit: deleteReport,
  onCommitted: loadList,
  onError: (e) => {
    console.error('Failed to delete report:', e)
    showNotice('Could not delete the report. It is back in the list.')
  },
  // Put the report back in the viewer if it was open.
  onUndo: (id, meta) => {
    if (meta && meta.open && !current.value) current.value = meta.open
  },
})

const visibleReports = computed(() => reports.value.filter((r) => !hiddenIds.value.has(r.id)))
const toastMessage = computed(() => (pendingDelete.value ? 'Report deleted.' : notice.value))

function onDelete(id) {
  const open = current.value && current.value.id === id ? current.value : null
  if (open) current.value = null
  removeReport(id, { open })
}

onBeforeUnmount(() => {
  flushDelete()
  clearTimeout(noticeTimer)
})

// Fetch the PDF as a blob (not a bare <a download>): shows a loading state while
// the server renders / a cold free-tier instance wakes, and surfaces a clear error
// instead of the browser's opaque "network error" download failure.
async function downloadPdf() {
  if (!current.value || !current.value.id || pdfLoading.value) return
  pdfLoading.value = true
  pdfError.value = ''
  try {
    const res = await fetch(`/reports/${current.value.id}/pdf`, { credentials: 'include' })
    if (!res.ok) {
      if (res.status === 401) {
        handleSessionExpired()
        return
      }
      throw new Error(`HTTP ${res.status}`)
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download =
      ('Humanitaria_' + (current.value.title || 'report'))
        .replace(/[^\w.-]+/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_|_$/g, '') + '.pdf'
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1500)
  } catch (e) {
    console.error('PDF download failed:', e)
    pdfError.value = 'Could not download the PDF. Please try again.'
  } finally {
    pdfLoading.value = false
  }
}

function scrollViewerBottom() {
  requestAnimationFrame(() => {
    if (viewer.value) viewer.value.scrollTop = viewer.value.scrollHeight
  })
}

async function generate() {
  if (!form.value.country || generating.value) return
  generating.value = true
  genError.value = ''
  current.value = {
    id: null,
    title: '',
    content: '',
    sources: null,
    report_type: form.value.report_type,
    cover_image: null,
    section_images: null,
    imagesStatus: null,
  }
  controller.value = new AbortController()
  try {
    const res = await fetch('/reports/stream', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        report_type: form.value.report_type,
        country: form.value.country,
        theme: form.value.theme || null,
        date_from: form.value.date_from || null,
        date_to: form.value.date_to || null,
        language: form.value.language,
      }),
      signal: controller.value.signal,
    })
    if (!res.ok) {
      if (res.status === 401) {
        handleSessionExpired()
        return
      }
      // 409 = per-user report limit; show the server's reason.
      const detail = res.status === 409 ? (await res.json().catch(() => ({}))).detail : null
      genError.value = detail || 'Could not generate the report. Please try again.'
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split(/\r?\n\r?\n/)
      buffer = parts.pop()
      for (const part of parts) {
        if (!part.trim()) continue
        const sse = parseSSE(part)
        if (!sse) continue
        if (sse.event === 'token') {
          try {
            current.value.content += JSON.parse(sse.data).content
            scrollViewerBottom()
          } catch (e) {}
        } else if (sse.event === 'sources') {
          try {
            current.value.sources = JSON.parse(sse.data).sources
          } catch (e) {}
        } else if (sse.event === 'images_status') {
          try {
            const d = JSON.parse(sse.data)
            current.value.imagesStatus =
              d.stage === 'cover'
                ? 'Generating cover illustration…'
                : `Illustrating “${d.heading}”…`
          } catch (e) {}
        } else if (sse.event === 'images') {
          try {
            const d = JSON.parse(sse.data)
            current.value.cover_image = d.cover
            current.value.section_images = d.sections
            current.value.imagesStatus = null
          } catch (e) {}
        } else if (sse.event === 'saved') {
          current.value.imagesStatus = null
          let rid = null
          try {
            const d = JSON.parse(sse.data)
            rid = d.report_id
            current.value.id = d.report_id
            current.value.title = d.title
          } catch (e) {}
          await loadList()
          // Swap the streamed (raw-citation) text for the stored, citation-normalised
          // version so the on-screen report matches the saved PDF exactly.
          if (rid) {
            try {
              const rep = await getReport(rid)
              current.value = {
                id: rep.id,
                title: rep.title,
                content: rep.content,
                sources: rep.sources,
                report_type: rep.report_type,
                cover_image: rep.cover_image,
                section_images: rep.section_images,
              }
            } catch (e) {}
          }
        } else if (sse.event === 'error') {
          try {
            genError.value = JSON.parse(sse.data).message
          } catch (e) {
            genError.value = 'Something went wrong.'
          }
        }
      }
    }
  } catch (e) {
    if (e?.name !== 'AbortError') {
      console.error('Report stream error:', e)
      genError.value =
        "Couldn't reach the server. It may be waking up (about 30 seconds); generate again."
    }
  } finally {
    generating.value = false
    controller.value = null
  }
}

// Citation chips ([n]) scroll to their source within the viewer (mirrors Chat.vue).
function onCiteClick(e) {
  if (e.target.closest && e.target.closest('.back-to-text')) {
    returnToCite(viewer.value)
    return
  }
  const cite = e.target.closest && e.target.closest('.cite')
  if (!cite) return
  e.preventDefault()
  revealSource(viewer.value, cite.getAttribute('data-cite'), cite)
}
</script>

<style scoped>
.reports-app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.reports-body {
  flex: 1;
  display: flex;
  min-height: 0;
}

.reports-aside {
  width: 320px;
  flex-shrink: 0;
  border-right: 1px solid var(--color-border);
  background-color: var(--color-surface-container-low);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: var(--space-4);
  gap: var(--space-5);
}

.report-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.form-title {
  font-family: var(--font-display);
  font-size: var(--text-base);
  font-weight: 700;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.field > span {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-muted);
}
.field-row {
  display: flex;
  gap: var(--space-2);
}
.field-row .field {
  flex: 1;
}

.field select,
.field input {
  width: 100%;
  padding: 8px 10px;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-text);
  background-color: var(--color-surface);
  border: 1px solid var(--color-outline);
  border-radius: var(--radius-md);
  outline: none;
}
.field select:focus,
.field input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 16%, transparent);
}

.generate-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  margin-top: var(--space-1);
  padding: 10px;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-on-accent);
  background-color: var(--color-accent-container);
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition:
    background-color 0.2s,
    transform 0.15s;
}
.generate-btn:hover:not(:disabled) {
  background-color: var(--color-accent);
}
.generate-btn:active:not(:disabled) {
  transform: scale(0.98);
}
.generate-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.form-hint {
  font-size: var(--text-xs);
  color: var(--color-muted);
}

.saved {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.saved-title-h {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-muted);
}
.saved-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.saved-item {
  display: flex;
  align-items: center;
  border-radius: var(--radius-md);
  transition: background-color 0.15s;
}
.saved-item:hover {
  background-color: var(--color-surface-container);
}
.saved-item.active {
  background-color: var(--color-surface-container-high);
}
.saved-open {
  flex: 1;
  min-width: 0;
  text-align: left;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: var(--space-2) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.saved-name {
  font-size: var(--text-sm);
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.saved-item.active .saved-name {
  color: var(--color-accent);
  font-weight: 600;
}
.saved-period {
  white-space: nowrap;
}
.saved-meta {
  font-family: var(--font-mono);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--color-muted);
}
.saved-del {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  margin-right: var(--space-1);
  border: none;
  background: transparent;
  color: var(--color-muted);
  border-radius: var(--radius-sm);
  cursor: pointer;
  opacity: 0;
  transition:
    opacity 0.15s,
    color 0.15s;
}
/* Visible on hover, on keyboard focus and always on touch screens (no hover). */
.saved-item:hover .saved-del,
.saved-item:focus-within .saved-del {
  opacity: 1;
}
@media (hover: none) {
  .saved-del {
    opacity: 1;
  }
}
.saved-del:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}
.saved-del:hover {
  color: var(--color-error);
}
.saved-skel {
  display: block;
  height: 32px;
  border-radius: var(--radius-md);
}

.report-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: var(--space-6) var(--space-8);
}

.report-column {
  max-width: 70ch;
  margin: 0 auto;
  font-size: var(--text-base);
}
.report-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}
.report-head-text {
  min-width: 0;
}
/* Document title: one clear step above the report's own section heads (xl). */
.report-title-h {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--color-text);
  text-wrap: balance;
  margin: 0;
}
.meta-part {
  white-space: nowrap;
}
.report-meta {
  display: flex;
  flex-wrap: wrap;
  column-gap: 1ch;
  margin: 6px 0 0;
  font-family: var(--font-mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}
.cover-img {
  display: block;
  width: 100%;
  margin: 0 0 var(--space-4);
  border-radius: var(--radius-lg);
}
.images-status {
  margin: 0 0 var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-muted);
  font-style: italic;
}
.report-content :deep(.section-img) {
  display: block;
  width: 100%;
  margin: 0.4em 0 1em;
  border-radius: var(--radius-md);
}

.report-actions {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
}
.pdf-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  text-decoration: none;
  transition:
    background-color 0.15s,
    color 0.15s,
    border-color 0.15s;
}
.pdf-btn:hover:not(:disabled) {
  background-color: var(--color-surface-container);
  color: var(--color-accent);
  border-color: var(--color-accent);
}
.pdf-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.pdf-error {
  margin: calc(-1 * var(--space-3)) 0 var(--space-4);
  text-align: right;
  font-size: var(--text-xs);
  color: var(--color-error);
}

.report-content {
  font-family: var(--font-body);
  font-size: var(--text-base);
  line-height: 1.65;
  color: var(--color-text);
}
.report-content :deep(h1) {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  margin: 0 0 0.5em;
}
.report-content :deep(h2) {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  margin: 1.1em 0 0.4em;
}
.report-content :deep(h3) {
  font-size: var(--text-lg);
  font-weight: 700;
  margin: 0.9em 0 0.3em;
}
.report-content :deep(p) {
  margin: 0 0 0.7em;
}
.report-content :deep(ul),
.report-content :deep(ol) {
  margin: 0.4em 0 0.8em;
  padding-left: 1.4em;
}
.report-content :deep(li) {
  margin-bottom: 0.35em;
}
.report-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.6em 0 1em;
  font-size: var(--text-sm);
}
.report-content :deep(th),
.report-content :deep(td) {
  border: 1px solid var(--color-border);
  padding: 6px 10px;
  text-align: left;
}
.report-content :deep(th) {
  background-color: var(--color-surface-container);
  font-weight: 600;
}

.report-loading {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.skel-line {
  display: block;
  height: 14px;
  border-radius: var(--radius-sm);
}
.skel-line.short {
  width: 55%;
}
.skel-line.title {
  width: 40%;
  height: 22px;
  margin-bottom: var(--space-3);
}
.saved-item.opening .saved-name {
  color: var(--color-text-secondary);
}

.report-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--color-muted);
  text-align: center;
}

.error-banner {
  margin: var(--space-4) 0 0;
  padding: var(--space-3) var(--space-4);
  background-color: var(--color-error-bg);
  color: var(--color-error);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 760px) {
  .reports-body {
    flex-direction: column;
  }
  .reports-aside {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
    max-height: 45%;
  }
  .report-main {
    padding: var(--space-4);
  }
}
</style>
