<template>
  <div class="reports-app">
    <header class="topbar">
      <router-link class="brand" to="/" title="Back to home">
        <HelpingHandLogo :size="32" :radius="10" />
        <div class="brand-text">
          <h1 class="brand-title">Humanitaria</h1>
          <span class="brand-sub">M&amp;E Reports</span>
        </div>
      </router-link>
      <div class="topbar-spacer"></div>
      <router-link to="/app" class="ghost-link" title="Back to chat">
        <MessageSquare :size="16" /> Chat
      </router-link>
      <UserMenu />
    </header>

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
              <input v-model="form.date_from" type="date" :disabled="generating" />
            </label>
            <label class="field">
              <span>To</span>
              <input v-model="form.date_to" type="date" :disabled="generating" />
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
        </form>

        <div class="saved">
          <h3 class="saved-title-h">Saved reports</h3>
          <template v-if="loadingList && !reports.length">
            <span v-for="n in 4" :key="'sk-' + n" class="skeleton saved-skel"></span>
          </template>
          <ul v-else-if="reports.length" class="saved-list">
            <li
              v-for="r in reports"
              :key="r.id"
              :class="['saved-item', { active: current && current.id === r.id }]"
            >
              <button type="button" class="saved-open" @click="openReport(r.id)">
                <span class="saved-name">{{ r.title }}</span>
                <span class="saved-meta">
                  {{ fmtDate(r.created_at) }} · {{ r.doc_count }} reports
                  <span v-if="reportTypeBadge(r.report_type)" class="type-badge saved-type-badge">{{
                    reportTypeBadge(r.report_type)
                  }}</span>
                </span>
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
        <template v-if="current">
          <img v-if="current.cover_image" class="cover-img" :src="current.cover_image" alt="" />
          <p v-if="current.imagesStatus" class="images-status">{{ current.imagesStatus }}</p>
          <div class="report-header">
            <h2 v-if="current.title" class="report-title-h">{{ current.title }}</h2>
            <span v-if="reportTypeBadge(current.report_type)" class="type-badge">{{
              reportTypeBadge(current.report_type)
            }}</span>
          </div>
          <div v-if="current.id" class="report-toolbar">
            <button type="button" class="pdf-btn" :disabled="pdfLoading" @click="downloadPdf">
              <Loader2 v-if="pdfLoading" :size="15" class="spin" />
              <FileDown v-else :size="15" />
              {{ pdfLoading ? 'Preparing…' : 'Download PDF' }}
            </button>
            <span v-if="pdfError" class="pdf-error">{{ pdfError }}</span>
          </div>
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
        </template>
        <div v-else class="report-empty">
          <FileText :size="40" />
          <p>Generate a situation report, or open a saved one.</p>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { MessageSquare, FileText, Trash2, Loader2, AlertCircle, FileDown } from 'lucide-vue-next'
import UserMenu from '../components/UserMenu.vue'
import HelpingHandLogo from '../components/HelpingHandLogo.vue'
import SourceList from '../components/SourceList.vue'
import { renderMarkdown } from '../utils/renderMarkdown.js'
import { injectSectionImages } from '../utils/reportImages.js'
import { parseSSE } from '../utils/parseSSE.js'
import { getReportOptions, listReports, getReport, deleteReport } from '../utils/reportsApi.js'
import { REPORT_TYPES, reportTypeBadge } from '../utils/reportTypes.js'
import { handleSessionExpired } from '../utils/authStore.js'

const countries = ref([])
const themes = ref([])
const optionsError = ref(false)

const reports = ref([])
const loadingList = ref(false)

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

function fmtDate(iso) {
  if (!iso) return ''
  return iso.slice(0, 10)
}

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
  } finally {
    loadingList.value = false
  }
}

async function openReport(id) {
  if (generating.value) return
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
  }
}

async function onDelete(id) {
  try {
    await deleteReport(id)
    if (current.value && current.value.id === id) current.value = null
    await loadList()
  } catch (e) {
    console.error('Failed to delete report:', e)
  }
}

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
      genError.value = 'Could not generate the report. Please try again.'
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
      genError.value = 'Connection lost. Please try again.'
    }
  } finally {
    generating.value = false
    controller.value = null
  }
}

// Citation chips ([n]) scroll to their source within the viewer (mirrors Chat.vue).
function onCiteClick(e) {
  const cite = e.target.closest && e.target.closest('.cite')
  if (!cite) return
  e.preventDefault()
  const id = cite.getAttribute('data-cite')
  const item = viewer.value && viewer.value.querySelector(`.source-item[data-srcid="${id}"]`)
  if (!item) return
  viewer.value
    .querySelectorAll('.source-item.active')
    .forEach((el) => el.classList.remove('active'))
  item.classList.add('active')
  item.scrollIntoView({ behavior: 'smooth', block: 'center' })
  item.classList.add('flash')
  setTimeout(() => item.classList.remove('flash'), 1500)
}
</script>

<style scoped>
.reports-app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.topbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
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
  min-width: 0;
}
.brand-title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-text);
  white-space: nowrap;
}
.brand-sub {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--color-muted);
  white-space: nowrap;
}
.topbar-spacer {
  flex: 1;
}

.ghost-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  text-decoration: none;
  transition:
    background-color 0.15s,
    color 0.15s;
}
.ghost-link:hover {
  background-color: var(--color-surface-container);
  color: var(--color-text);
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
.saved-meta {
  font-size: 11px;
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
.saved-item:hover .saved-del {
  opacity: 1;
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
  scroll-behavior: smooth;
}

.report-header {
  max-width: 75ch;
  margin: 0 auto var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.report-title-h {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  color: var(--color-text);
  margin: 0;
}
.type-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 9px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-accent);
  background-color: var(--color-surface-container);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  white-space: nowrap;
}
.saved-type-badge {
  margin-left: 6px;
}
.cover-img {
  display: block;
  max-width: 75ch;
  width: 100%;
  margin: 0 auto var(--space-4);
  border-radius: var(--radius-lg);
}
.images-status {
  max-width: 75ch;
  margin: 0 auto var(--space-2);
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

.report-toolbar {
  max-width: 75ch;
  margin: 0 auto var(--space-3);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}
.pdf-btn {
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
  font-size: var(--text-xs);
  color: var(--color-error);
}

.report-content {
  max-width: 75ch;
  margin: 0 auto;
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
  max-width: 75ch;
  margin: 0 auto;
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
  max-width: 75ch;
  margin: var(--space-4) auto 0;
  padding: var(--space-3) var(--space-4);
  background-color: var(--color-error-bg);
  color: var(--color-error);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.report-main :deep(.sources) {
  max-width: 75ch;
  margin-left: auto;
  margin-right: auto;
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
