<template>
  <div class="reports-app">
    <AppTopbar context="M&amp;E Reports" />

    <div :class="['reports-body', { 'has-report': !!(current || openingId) }]">
      <aside class="reports-aside">
        <!-- With saved reports, the form waits behind one button so the library
             is in view; Run next period and generation open it. -->
        <button
          v-if="!showForm"
          ref="newReportBtn"
          type="button"
          class="new-report-btn"
          @click="openForm"
        >
          <Plus :size="16" aria-hidden="true" />
          New report
        </button>
        <form v-else class="report-form" @submit.prevent="generate">
          <h2 ref="formTitle" class="form-title" tabindex="-1">New report</h2>

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

          <!-- "Run next period": the new report continues a saved one and opens
               with what changed since then. -->
          <div v-if="continuation && !generating" class="continues" role="status">
            <template v-if="continuesSeries">
              <p>
                Continues <strong>{{ continuation.name }}</strong
                >, <span class="continues-period">{{ continuation.period }}</span
                >. The new report opens with what changed since then.
              </p>
              <p v-if="continuationNotes.endClamped" class="form-hint">
                The period ends today, because it isn't over yet.
              </p>
              <p v-if="continuationNotes.startClamped" class="form-hint">
                The start moved to {{ minDate }}: older documents are no longer indexed.
              </p>
            </template>
            <p v-else>
              These settings differ from <strong>{{ continuation.name }}</strong
              >, so this report won't be compared with it.
            </p>
            <button type="button" class="continues-clear" @click="continuation = null">
              {{ continuesSeries ? "Don't compare with the previous report" : 'Dismiss' }}
            </button>
          </div>

          <!-- While a report streams, Generate becomes Stop (Chat's Charcoal Stop). -->
          <button
            v-if="generating"
            ref="stopBtn"
            type="button"
            class="generate-btn stop-gen"
            @click="stopGeneration"
          >
            <Square :size="14" aria-hidden="true" />
            Stop generating
          </button>
          <button
            v-else
            ref="generateBtn"
            type="submit"
            class="generate-btn"
            :disabled="!form.country"
          >
            <FileText :size="16" />
            Generate report
          </button>

          <p v-if="optionsError" class="form-hint">Could not load options. Try refreshing.</p>
          <p v-else-if="!countries.length" class="form-hint">Preparing the country list…</p>
          <p v-else-if="!form.country && !generating" class="form-hint">
            Choose a country to generate a report.
          </p>
        </form>

        <div class="saved">
          <h3 class="saved-title-h">Saved reports</h3>
          <p v-if="generating" class="form-hint">
            Saved reports open when this report finishes, or after you stop it.
          </p>
          <template v-if="loadingList && !reports.length">
            <span v-for="n in 4" :key="'sk-' + n" class="skeleton saved-skel"></span>
          </template>
          <ul v-else-if="savedEntries.length" class="saved-list">
            <template
              v-for="(e, i) in savedEntries"
              :key="e.kind === 'single' ? e.report.id : 'series:' + e.key"
            >
              <li
                v-if="e.kind === 'single'"
                :class="[
                  'saved-item',
                  {
                    active: current && current.id === e.report.id,
                    opening: openingId === e.report.id,
                  },
                ]"
                :aria-busy="openingId === e.report.id ? 'true' : undefined"
              >
                <button
                  type="button"
                  class="saved-open"
                  :title="e.report.title"
                  :aria-disabled="generating ? 'true' : undefined"
                  @click="openReport(e.report.id)"
                >
                  <span class="saved-name">{{ savedName(e.report) }}</span>
                  <span class="saved-meta"
                    >{{ savedType(e.report)
                    }}<template v-if="savedPeriod(e.report)"
                      >{{ ' ' }}<!-- The separator travels with the period, so a wrapped line
                           starts with "·" instead of leaving one at a line end. --><span
                        class="saved-period"
                        >· {{ savedPeriod(e.report) }}</span
                      ></template
                    ></span
                  >
                </button>
                <button
                  type="button"
                  class="saved-del"
                  :aria-label="deleteLabel(e.report)"
                  @click.stop="onDelete(e.report.id)"
                >
                  <Trash2 :size="13" />
                </button>
              </li>

              <!-- A series: same type + country + sector + language, one row that
                   expands to its periods, newest first. -->
              <li
                v-else
                :class="[
                  'saved-series',
                  {
                    expanded: expandedSeries.has(e.key),
                    'holds-active': current && e.reports.some((r) => r.id === current.id),
                  },
                ]"
              >
                <button
                  type="button"
                  class="saved-series-head"
                  :aria-expanded="expandedSeries.has(e.key) ? 'true' : 'false'"
                  :aria-controls="'saved-series-' + i"
                  @click="toggleSeries(e.key)"
                >
                  <span class="saved-series-text">
                    <span class="saved-name">{{ savedName(e.latest) }}</span>
                    <span class="saved-meta"
                      >{{ savedType(e.latest) }} · {{ e.reports.length }} reports{{ ' '
                      }}<span v-if="e.latest.date_to" class="saved-period"
                        >· to {{ e.latest.date_to }}</span
                      ></span
                    >
                  </span>
                  <ChevronRight :size="14" class="saved-series-chevron" aria-hidden="true" />
                </button>
                <ul
                  v-show="expandedSeries.has(e.key)"
                  :id="'saved-series-' + i"
                  class="saved-periods"
                >
                  <li
                    v-for="r in e.reports"
                    :key="r.id"
                    :class="[
                      'saved-item',
                      { active: current && current.id === r.id, opening: openingId === r.id },
                    ]"
                    :aria-busy="openingId === r.id ? 'true' : undefined"
                  >
                    <button
                      type="button"
                      class="saved-open"
                      :title="r.title"
                      :aria-disabled="generating ? 'true' : undefined"
                      @click="openReport(r.id)"
                    >
                      <span class="saved-name saved-period-name">{{
                        savedPeriod(r) || 'No period set'
                      }}</span>
                    </button>
                    <button
                      type="button"
                      class="saved-del"
                      :aria-label="deleteLabel(r)"
                      @click.stop="onDelete(r.id)"
                    >
                      <Trash2 :size="13" />
                    </button>
                  </li>
                </ul>
              </li>
            </template>
          </ul>
          <p v-else class="form-hint">No saved reports yet.</p>
        </div>
      </aside>

      <main ref="viewer" class="report-main" @click="onCiteClick">
        <!-- Phones show the library or one report, never both stacked. -->
        <button
          v-if="current || openingId"
          type="button"
          class="back-to-list"
          @click="generating ? stopAndShowList() : closeReport()"
        >
          <ArrowLeft :size="15" aria-hidden="true" />
          {{ generating ? 'Stop and show all reports' : 'All reports' }}
        </button>
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
              <p v-if="comparedWith" class="report-compared">
                <template v-if="comparedWith.deleted">
                  Compared with an earlier report that has since been deleted.
                </template>
                <template v-else>
                  Compared with
                  <button
                    type="button"
                    class="report-compared-link"
                    @click="openReport(comparedWith.id)"
                  >
                    {{ comparedWith.period || 'the previous report' }}
                  </button>
                </template>
              </p>
              <!-- A series is implicit: a report made as a one-off can sit after an
                   earlier period it was never compared with. Say so. -->
              <p v-if="notComparedWith" class="report-compared">
                Not compared with the report for
                <button
                  type="button"
                  class="report-compared-link"
                  @click="openReport(notComparedWith.id)"
                >
                  {{ savedPeriod(notComparedWith) || 'the earlier period' }}
                </button>
              </p>
              <!-- An older period links forward instead of offering "Run next period",
                   which would continue a different (newer) report. -->
              <p v-if="continuedBy" class="report-compared">
                Continued by
                <button
                  type="button"
                  class="report-compared-link"
                  @click="openReport(continuedBy.id)"
                >
                  {{ savedPeriod(continuedBy) || 'a later report' }}
                </button>
              </p>
              <p v-else-if="nextSuggestion && nextSuggestion.notStarted" class="report-compared">
                Next period starts {{ nextSuggestion.startsOn }}
              </p>
            </div>
            <div v-if="current.id" class="report-actions">
              <button
                v-if="nextSuggestion && !nextSuggestion.notStarted"
                type="button"
                class="pdf-btn"
                :disabled="generating"
                @click="runNextPeriod"
              >
                <CalendarPlus :size="15" />
                Run next period
              </button>
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
            <!-- The report model reads all sources before writing its first word
                 (about a minute and a half), so the wait is named, not silent. -->
            <p class="report-loading-note" role="status">
              Reading the sources. The first words usually appear within two minutes.
            </p>
            <span class="skeleton skel-line"></span>
            <span class="skeleton skel-line"></span>
            <span class="skeleton skel-line short"></span>
          </div>
          <article
            v-else
            class="report-content"
            v-html="
              injectComparisonNote(
                injectSectionImages(
                  renderMarkdown(current.content, current.sources),
                  current.section_images,
                ),
                comparisonNote({
                  checking: current.checking,
                  period: current.comparedPeriod,
                  removed: current.checkRemoved,
                }),
              )
            "
          ></article>
          <p v-if="current.stopped" class="stopped-note" role="status">
            Stopped. This report was not saved.
          </p>
          <!-- Chat's error: hairline border, the alert icon and "Try again" in place;
               the form still holds what was asked for. -->
          <div v-if="genError" class="error-banner">
            <AlertCircle :size="16" class="error-icon" aria-hidden="true" />
            <span class="error-text">{{ genError }}</span>
            <button
              v-if="!generating && form.country"
              type="button"
              class="retry-btn"
              @click="generate"
            >
              <RotateCcw :size="14" aria-hidden="true" />
              Try again
            </button>
          </div>
          <SourceList v-if="current.sources" :sources="current.sources" />
        </div>
        <!-- Nothing open: Chat's empty pattern (left-aligned promise, coverage line,
             hairline rows), with the user's series as the starting points. -->
        <div v-else class="report-empty">
          <div class="empty-inner">
            <h2 class="empty-title">Build an M&amp;E report from the record.</h2>
            <p class="empty-lede">
              Each report draws on many ReliefWeb reports at once and cites every one, so you can
              check it and quote it.
            </p>
            <template v-if="emptyRows.length">
              <p class="empty-pick">
                {{
                  emptyRows[0].series
                    ? 'Pick up a series where it left off.'
                    : 'Open a recent report.'
                }}
              </p>
              <ul
                class="empty-list"
                :aria-label="emptyRows[0].series ? 'Your report series' : 'Recent reports'"
              >
                <li v-for="row in emptyRows" :key="row.report.id">
                  <button type="button" class="empty-row" @click="openReport(row.report.id)">
                    <span class="empty-row-text">
                      <span class="empty-row-name">{{ savedName(row.report) }}</span>
                      <span class="empty-row-meta">{{ row.meta }}</span>
                    </span>
                    <ArrowRight :size="15" class="empty-row-arrow" aria-hidden="true" />
                  </button>
                </li>
              </ul>
            </template>
          </div>
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
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  FileText,
  Trash2,
  Loader2,
  AlertCircle,
  FileDown,
  Copy,
  Check,
  ArrowLeft,
  ArrowRight,
  ChevronRight,
  CalendarPlus,
  Square,
  Plus,
  RotateCcw,
} from 'lucide-vue-next'
import AppTopbar from '../components/AppTopbar.vue'
import SourceList from '../components/SourceList.vue'
import UndoToast from '../components/UndoToast.vue'
import CitePreview from '../components/CitePreview.vue'
import { useUndoableDelete } from '../utils/undoableDelete.js'
import { renderMarkdown } from '../utils/renderMarkdown.js'
import { injectSectionImages } from '../utils/reportImages.js'
import { comparisonNote, injectComparisonNote } from '../utils/comparisonNote.js'
import { revealSource, returnToCite } from '../utils/sources.js'
import { parseSSE } from '../utils/parseSSE.js'
import { getReportOptions, listReports, getReport, deleteReport } from '../utils/reportsApi.js'
import { REPORT_TYPES, reportTypeBadge } from '../utils/reportTypes.js'
import { splitReportTitle } from '../utils/reportTitle.js'
import { groupSeries, newerInSeries, olderInSeries, seriesKey } from '../utils/reportSeries.js'
import { nextPeriod } from '../utils/nextPeriod.js'
import { copyWithSources } from '../utils/citationCopy.js'
import { localIsoDay, minReportDate, maxReportDate } from '../utils/reportDateBounds.js'
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
const route = useRoute()
const router = useRouter()

const form = ref({
  report_type: 'situation',
  country: '',
  theme: '',
  date_from: '',
  date_to: '',
  language: 'en',
})

const current = ref(null) // a saved report as toCurrent() shapes it, or the one streaming

// The viewer's copy of a saved report. The series fields (type, country, sector,
// language, period, previous_report_id) drive "Run next period" and "Compared with".
function toCurrent(rep) {
  return {
    id: rep.id,
    title: rep.title,
    content: rep.content,
    sources: rep.sources,
    report_type: rep.report_type,
    country: rep.country,
    theme: rep.theme,
    language: rep.language,
    date_from: rep.date_from,
    date_to: rep.date_to,
    previous_report_id: rep.previous_report_id || null,
    cover_image: rep.cover_image,
    section_images: rep.section_images,
  }
}
const generating = ref(false)
const genError = ref('')
const viewer = ref(null)
const controller = ref(null)

const pdfLoading = ref(false)
const pdfError = ref('')

// Default period: the last three months, in local calendar days (like the bounds).
function setDefaultDates() {
  const to = new Date()
  const from = new Date()
  from.setMonth(from.getMonth() - 3)
  form.value.date_from = localIsoDay(from)
  form.value.date_to = localIsoDay(to)
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

// Each delete button names its report: a list of identical "Delete report"
// buttons does not say which one a screen-reader user is about to remove.
function deleteLabel(r) {
  const period = savedPeriod(r)
  return `Delete report: ${savedName(r)}, ${savedType(r)}${period ? `, ${period}` : ''}`
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

// Back/Forward or an edited URL: open the named report, or return to the library.
watch(
  () => route.query.report,
  (id) => {
    if (!id) {
      if (current.value && !generating.value) current.value = null
      return
    }
    if (id === openingId.value || (current.value && current.value.id === id)) return
    openReport(id, { fromRoute: true })
  },
  { immediate: true },
)

// Tab title names the open report ("Afghanistan · Situation Report · Humanitaria").
watch(
  () => [titleParts.value.heading, current.value && current.value.report_type],
  ([heading, type]) => {
    document.title = heading
      ? `${heading} · ${typeLabel(type)} · Humanitaria`
      : 'M&E reports · Humanitaria'
  },
  { immediate: true },
)

async function loadList() {
  loadingList.value = true
  try {
    reports.value = (await listReports()).reports || []
    listLoaded.value = true
  } catch (e) {
    console.error('Failed to load reports:', e)
    showNotice('Could not load your saved reports. Try refreshing the page.')
  } finally {
    loadingList.value = false
  }
}

// The open report lives in the URL (/reports?report=<id>) so Back/Forward,
// bookmarks, new tabs and shared links work. A query, not /reports/:id: that
// path is the JSON API (api/routes/reports.py) and would shadow the page on reload.

// Returns the navigation promise (resolved at once when nothing changes), so a
// caller can wait for the route watcher to settle.
function syncUrl(id, { push = false } = {}) {
  const want = id || undefined
  if ((route.query.report || undefined) === want) return Promise.resolve()
  const query = { ...route.query }
  if (want) query.report = want
  else delete query.report
  return (push ? router.push : router.replace)({ query })
}

function closeReport() {
  syncUrl(null, { push: true })
}

// Stop a streaming report: the request is aborted, the server stops generating
// and nothing is saved (reports are saved only after a complete stream).
function stopGeneration() {
  if (controller.value) controller.value.abort()
}

// Phones show one pane; leaving the streaming report stops it first.
function stopAndShowList() {
  stopGeneration()
  current.value = null
  closeReport()
}

async function openReport(id, { fromRoute = false } = {}) {
  if (generating.value) return
  openingId.value = id
  if (!fromRoute) syncUrl(id, { push: true })
  try {
    const rep = await getReport(id)
    current.value = toCurrent(rep)
    genError.value = ''
    nextTick(() => {
      if (viewer.value) viewer.value.scrollTop = 0
    })
  } catch (e) {
    console.error('Failed to open report:', e)
    showNotice('Could not open the report. Try again.')
    if (!current.value || current.value.id !== id) syncUrl(null)
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
    if (meta && meta.open && !current.value) {
      current.value = meta.open
      syncUrl(id)
    }
  },
})

const visibleReports = computed(() => reports.value.filter((r) => !hiddenIds.value.has(r.id)))
// The saved list with each series folded into one expandable row.
const savedEntries = computed(() => groupSeries(visibleReports.value))

// Series rows the user opened. The series holding the open report opens with it,
// so the active period is always visible in the list.
const expandedSeries = ref(new Set())
function toggleSeries(key) {
  const next = new Set(expandedSeries.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedSeries.value = next
}
// Keyed from the list row, which always carries the series fields (a just-generated
// report can be open before the list reloads; the watch fires again once it does).
const activeSeriesKey = computed(() => {
  const id = current.value && current.value.id
  const row = id && reports.value.find((r) => r.id === id)
  return row ? seriesKey(row) : null
})
watch(activeSeriesKey, (key) => {
  if (key && !expandedSeries.value.has(key)) {
    expandedSeries.value = new Set([...expandedSeries.value, key])
  }
})
// --- Run next period ---------------------------------------------------------
// The series continues from its latest period, whichever of its reports is open
// (an older one's "next period" usually exists already). Falls back to the open
// report until the list carries it.
const seriesLatest = computed(() => {
  const id = current.value && current.value.id
  if (!id) return null
  for (const e of savedEntries.value) {
    if (e.kind === 'single' && e.report.id === id) return e.report
    if (e.kind === 'series' && e.reports.some((r) => r.id === id)) return e.latest
  }
  return current.value
})
// Starting points in the empty viewer: the user's series (latest report, and
// whether its next period can be run yet), else their most recent reports.
const emptyRows = computed(() => {
  const series = savedEntries.value.filter((e) => e.kind === 'series').slice(0, 4)
  if (series.length) {
    return series.map((e) => {
      const next = nextPeriod(e.latest, new Date())
      const when = !next
        ? e.latest.date_to
          ? `to ${e.latest.date_to}`
          : ''
        : next.notStarted
          ? `next period starts ${next.startsOn}`
          : `next period ready, from ${next.date_from}`
      return {
        series: true,
        report: e.latest,
        meta: [savedType(e.latest), `${e.reports.length} reports`, when]
          .filter(Boolean)
          .join(' · '),
      }
    })
  }
  return savedEntries.value.slice(0, 3).map((e) => ({
    series: false,
    report: e.report,
    meta: [savedType(e.report), savedPeriod(e.report)].filter(Boolean).join(' · '),
  }))
})

// The earlier period of the open report's series that it was not compared with
// (made as a one-off, so no previous_report_id).
const notComparedWith = computed(() => {
  const c = current.value
  if (!c || !c.id || c.previous_report_id) return null
  return olderInSeries(visibleReports.value, c.id)
})
// The open report's next newer period in its series, when it is not the latest.
const continuedBy = computed(() =>
  current.value && current.value.id ? newerInSeries(visibleReports.value, current.value.id) : null,
)
// The series' next period (nextPeriod.js), offered only on its latest report;
// null when there is no period to carry or the open report is an older period.
const nextSuggestion = computed(() =>
  seriesLatest.value && !continuedBy.value ? nextPeriod(seriesLatest.value, new Date()) : null,
)
// Set by "Run next period": the saved report the form's next report continues.
const continuation = ref(null)
const generateBtn = ref(null)
const stopBtn = ref(null)
// The link holds only while the form keeps the series' type, country, sector and
// language (the API refuses a mismatch); dates may change.
const continuesSeries = computed(
  () =>
    !!continuation.value &&
    seriesKey({ ...form.value, theme: form.value.theme || null }) === continuation.value.key,
)
// Clamp notes describe the suggested dates; once edited, they no longer apply.
const continuationNotes = computed(() => {
  const c = continuation.value
  const same = c && form.value.date_from === c.date_from && form.value.date_to === c.date_to
  return { endClamped: same && c.endClamped, startClamped: same && c.startClamped }
})

// The "New report" form: open for a first-time user (no saved reports), while a
// next period is being set up or generated, or once the user asks for it.
const formOpen = ref(false)
const listLoaded = ref(false)
const newReportBtn = ref(null)
const formTitle = ref(null)
const showForm = computed(
  () =>
    formOpen.value ||
    !!continuation.value ||
    generating.value ||
    (listLoaded.value && !reports.value.length),
)
function openForm() {
  formOpen.value = true
  nextTick(() => formTitle.value && formTitle.value.focus())
}

function runNextPeriod() {
  const rep = seriesLatest.value
  const s = nextSuggestion.value
  if (!rep || !s || s.notStarted || generating.value) return
  formOpen.value = true // stays open if the user then makes it a one-off
  form.value = {
    report_type: rep.report_type || 'situation',
    country: rep.country || '',
    theme: rep.theme || '',
    date_from: s.date_from,
    date_to: s.date_to,
    language: rep.language || 'en',
  }
  continuation.value = {
    id: rep.id,
    key: seriesKey(rep),
    name: savedName(rep),
    period: savedPeriod(rep),
    date_from: s.date_from,
    date_to: s.date_to,
    endClamped: s.endClamped,
    startClamped: s.startClamped,
  }
  // Phones show one pane: go back to the form. Wide screens keep the report open.
  if (window.matchMedia('(max-width: 760px)').matches) closeReport()
  nextTick(() => {
    if (generateBtn.value) {
      generateBtn.value.scrollIntoView({ block: 'center' })
      generateBtn.value.focus({ preventScroll: true })
    }
  })
}

// "Compared with <period>" under the open report's title, from the saved list.
const comparedWith = computed(() => {
  const pid = current.value && current.value.previous_report_id
  if (!pid) return null
  const row = reports.value.find((r) => r.id === pid)
  if (row) return { id: pid, period: savedPeriod(row) }
  return loadingList.value ? null : { deleted: true }
})

const toastMessage = computed(() => (pendingDelete.value ? 'Report deleted.' : notice.value))

function onDelete(id) {
  const open = current.value && current.value.id === id ? current.value : null
  if (open) {
    current.value = null
    syncUrl(null)
  }
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
  formOpen.value = true // the form stays put when the report is saved
  // Generate is replaced by Stop; keep keyboard focus on the control that is there.
  nextTick(() => stopBtn.value && stopBtn.value.focus())
  genError.value = ''
  // Clear the open report from the URL BEFORE the request: the route watcher
  // closes the viewer when ?report= disappears and nothing is generating, so a
  // fast error (404/409/422) answered before the navigation settled used to
  // close the viewer and hide its own message.
  await syncUrl(null)
  current.value = {
    id: null,
    title: '',
    content: '',
    sources: null,
    report_type: form.value.report_type,
    cover_image: null,
    section_images: null,
    imagesStatus: null,
    // The period this report is compared with, for the note under "What changed".
    comparedPeriod: continuesSeries.value ? continuation.value.period : null,
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
        previous_report_id: continuesSeries.value ? continuation.value.id : null,
      }),
      signal: controller.value.signal,
    })
    if (!res.ok) {
      if (res.status === 401) {
        handleSessionExpired()
        return
      }
      // The report this one continues was deleted, or no longer matches it.
      if (continuesSeries.value && (res.status === 404 || res.status === 422)) {
        continuation.value = null
        genError.value =
          res.status === 404
            ? 'The report this one continues was deleted, so there is nothing to compare against. Generate again without the comparison.'
            : 'The settings no longer match the report this one continues. Generate again without the comparison.'
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
        } else if (sse.event === 'status') {
          try {
            // Next-period reports: the streamed "What changed" is checked before it
            // is saved; the note under its heading says so, then what the check did.
            const d = JSON.parse(sse.data)
            if (d.stage === 'checking_comparison') {
              current.value.checking = true
            } else if (d.stage === 'comparison_checked') {
              current.value.checking = false
              current.value.checkRemoved = d.removed
            }
          } catch (e) {}
        } else if (sse.event === 'saved') {
          continuation.value = null
          current.value.imagesStatus = null
          current.value.checking = false
          let rid = null
          try {
            const d = JSON.parse(sse.data)
            rid = d.report_id
            current.value.id = d.report_id
            syncUrl(d.report_id)
            current.value.title = d.title
          } catch (e) {}
          await loadList()
          // Swap the streamed (raw-citation) text for the stored, citation-normalised
          // version so the on-screen report matches the saved PDF exactly.
          if (rid) {
            try {
              const rep = await getReport(rid)
              const { checkRemoved, comparedPeriod } = current.value
              current.value = { ...toCurrent(rep), checkRemoved, comparedPeriod }
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
    if (e?.name === 'AbortError') {
      if (current.value) current.value.stopped = true
    } else {
      console.error('Report stream error:', e)
      genError.value =
        "Couldn't reach the server. It may be waking up (about 30 seconds); generate again."
    }
  } finally {
    if (current.value) current.value.checking = false
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

.back-to-list {
  display: none;
  align-items: center;
  gap: 6px;
  margin-bottom: var(--space-4);
  padding: 4px 8px 4px 4px;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-accent);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.back-to-list:hover {
  background-color: var(--color-accent-soft);
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
/* The collapsed form: DESIGN's secondary button, full rail width. */
.new-report-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  width: 100%;
  padding: 10px;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition:
    color 0.15s,
    border-color 0.15s;
}
.new-report-btn:hover {
  color: var(--color-accent);
  border-color: var(--color-accent);
}
.new-report-btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
.form-title:focus {
  outline: none;
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
/* Same label as Settings and Admin. Small text on the Reading Room rail uses
   Graphite: Margin Gray is 4.35:1 there, just under AA. */
.field > span {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
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
/* Disabled reads as off in both themes: a neutral shelf fill, not a faded green
   (dark theme's bright green at 55% still looked live). */
.generate-btn:disabled {
  color: var(--color-muted);
  background-color: var(--color-surface-container-high);
  cursor: not-allowed;
}
/* Stop while a report streams: Chat's Charcoal Stop (DESIGN, Buttons). */
.generate-btn.stop-gen {
  color: var(--color-on-tertiary);
  background-color: var(--color-tertiary);
}
.generate-btn.stop-gen:hover {
  background-color: var(--color-text-secondary);
}
.saved-open[aria-disabled='true'] {
  cursor: not-allowed;
}
.stopped-note {
  margin: var(--space-3) 0 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.form-hint {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

/* "Run next period": what the next report continues, above Generate. */
.continues {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  background-color: var(--color-surface-container-low);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  line-height: 1.45;
  color: var(--color-text);
}
.continues p {
  margin: 0;
}
.continues-period {
  font-family: var(--font-mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.continues-clear,
.report-compared-link {
  padding: 0;
  border: none;
  background: none;
  font: inherit;
  color: var(--color-accent);
  text-decoration: underline;
  text-underline-offset: 2px;
  cursor: pointer;
}
.continues-clear {
  font-size: var(--text-xs);
}
.continues-clear:focus-visible,
.report-compared-link:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: 2px;
}

.saved {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.saved-title-h {
  font-family: var(--font-display);
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--color-text);
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
  color: var(--color-text-secondary);
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

/* Series: one row that opens to its periods (newest first). */
.saved-series-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  text-align: left;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  padding: var(--space-2) var(--space-3);
  transition: background-color 0.15s;
}
.saved-series-head:hover {
  background-color: var(--color-surface-container);
}
.saved-series-head:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}
.saved-series-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.saved-series-chevron {
  flex-shrink: 0;
  color: var(--color-muted);
  transition: transform 0.15s;
}
.saved-series.expanded .saved-series-chevron {
  transform: rotate(90deg);
}
/* Folded with the open report inside: the row says where the report lives. */
.saved-series.holds-active:not(.expanded) .saved-name {
  color: var(--color-accent);
  font-weight: 600;
}
.saved-periods {
  list-style: none;
  margin: 2px 0 var(--space-1) var(--space-4);
  padding: 0 0 0 var(--space-1);
  border-left: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.saved-periods .saved-open {
  padding-block: 6px;
}
.saved-period-name {
  font-family: var(--font-mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
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
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3) var(--space-4);
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}
/* Title takes the room it needs; on a narrow column the actions wrap below it
   instead of squeezing it to a few letters. */
.report-head-text {
  flex: 1 1 16rem;
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
/* Under the "What changed" heading of a just-generated next-period report:
   checking, then what the check removed (utils/comparisonNote.js). */
.report-content :deep(.compare-note) {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: calc(-1 * var(--space-1)) 0 var(--space-3);
  font-size: var(--text-sm);
  line-height: 1.45;
  color: var(--color-text-secondary);
}
.report-content :deep(.compare-note-spin) {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  border: 1.5px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
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

.report-compared {
  margin: 4px 0 0;
  font-family: var(--font-mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}
/* Three actions no longer fit beside the title, so they sit on their own row
   under the meta line. The row may shrink (min-width: 0) so its buttons wrap on
   a phone instead of pushing the page sideways. */
.report-actions {
  flex: 0 1 auto;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
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
.report-loading-note {
  margin: 0 0 var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
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

/* Nothing open: Chat's empty pattern (EmptyState.vue), left-aligned at 560px. */
.report-empty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6) var(--space-4);
}
.empty-inner {
  width: 100%;
  max-width: 560px;
}
.empty-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--color-text);
}
.empty-lede {
  margin: var(--space-2) 0 0;
  max-width: 48ch;
  font-size: 15px;
  line-height: 1.55;
  color: var(--color-text-secondary);
}
.empty-pick {
  margin: var(--space-6) 0 var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}
.empty-list {
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: 1px solid var(--color-border);
}
.empty-list li {
  border-bottom: 1px solid var(--color-border);
}
.empty-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-3) var(--space-2);
  text-align: left;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background-color 0.15s;
}
.empty-row:hover {
  background-color: var(--color-surface-container-low);
}
.empty-row:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
.empty-row-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.empty-row-name {
  font-size: var(--text-sm);
  color: var(--color-text);
}
.empty-row-meta {
  font-family: var(--font-mono);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}
.empty-row-arrow {
  flex-shrink: 0;
  color: var(--color-muted);
  transition:
    color 0.15s,
    transform 0.15s;
}
.empty-row:hover .empty-row-arrow {
  color: var(--color-accent);
  transform: translateX(2px);
}

/* As in Chat: a full hairline tinted from the error color, never a side rule. */
.error-banner {
  margin: var(--space-4) 0 0;
  padding: var(--space-3) var(--space-4);
  border: 1px solid color-mix(in oklch, var(--color-error) 35%, transparent);
  background-color: var(--color-error-bg);
  color: var(--color-error);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.error-text {
  flex: 1;
  min-width: 0;
}
.error-icon {
  flex-shrink: 0;
}
.retry-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-error);
  background: transparent;
  border: 1px solid color-mix(in oklch, var(--color-error) 45%, transparent);
  border-radius: var(--radius-md);
  cursor: pointer;
}
.retry-btn:hover {
  background-color: color-mix(in oklch, var(--color-error) 10%, transparent);
}
.retry-btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
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
  /* One pane at a time: the library, or the open report with a way back. The
     old 45% library strip above the report gave two nested scroll areas. */
  .reports-aside {
    flex: 1;
    width: 100%;
    border-right: none;
  }
  .reports-body.has-report .reports-aside {
    display: none;
  }
  .reports-body:not(.has-report) .report-main {
    display: none;
  }
  .report-main {
    padding: var(--space-4);
  }
  .back-to-list {
    display: inline-flex;
  }
}
</style>
