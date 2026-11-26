<template>
  <div class="reports-app">
    <AppTopbar :context="t('reports.topbar')" />

    <div :class="['reports-body', { 'has-main': mainPane }]">
      <aside class="reports-aside">
        <!-- The form lives in the main column. While a report streams, the button
             waits like the saved rows. -->
        <button type="button" class="new-report-btn" :disabled="generating" @click="openForm">
          <Plus :size="16" aria-hidden="true" />
          {{ t('reports.newReport') }}
        </button>

        <div class="saved">
          <h3 class="saved-title-h">{{ t('reports.saved.title') }}</h3>
          <p v-if="generating" class="form-hint">
            {{ t('reports.saved.waitWhileGenerating') }}
          </p>
          <template v-if="loadingList && !reports.length">
            <span v-for="n in 4" :key="'sk-' + n" class="skeleton saved-skel"></span>
          </template>
          <ul v-else-if="visibleReports.length" class="saved-list">
            <li
              v-for="r in visibleReports"
              :key="r.id"
              :class="[
                'saved-item',
                {
                  active: current && current.id === r.id,
                  opening: openingId === r.id,
                },
              ]"
              :aria-busy="openingId === r.id ? 'true' : undefined"
            >
              <button
                type="button"
                class="saved-open"
                :title="rowTitle(r)"
                :aria-disabled="generating ? 'true' : undefined"
                @click="openReport(r.id)"
              >
                <!-- Country, then the sector in full (none for all sectors), then
                     the short type and language code, and the period. -->
                <span class="saved-name">{{ shownCountry(r) }}</span>
                <span v-if="shownSector(r)" class="saved-sector">{{ shownSector(r) }}</span>
                <span class="saved-meta">
                  <!-- The report's language as its code, so an English and a Turkish
                       report with the same settings can be told apart. The "·" is
                       glued to the type by a no-break space, so no line starts with
                       a separator. Screen readers hear the full type name. -->
                  <span
                    ><span aria-hidden="true">{{ savedTypeShort(r) }}</span
                    ><span class="sr-only">{{ savedType(r) }}</span
                    ><span v-if="reportLanguage(r)" class="saved-lang"
                      >{{ '\u00a0· '
                      }}<span class="saved-lang-code" aria-hidden="true">{{
                        reportLanguage(r).toUpperCase()
                      }}</span
                      ><span class="sr-only">{{ languageLabel(r) }}</span></span
                    ></span
                  >
                  <span v-if="savedPeriod(r)" class="saved-period">{{ savedPeriod(r) }}</span>
                </span>
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
          <p v-else class="form-hint">{{ t('reports.saved.empty') }}</p>
        </div>
      </aside>

      <main ref="viewer" class="report-main" @click="onCiteClick">
        <!-- Phones show the library, the form or one report, never two stacked. -->
        <button v-if="showBack" type="button" class="back-to-list" @click="backToList">
          <ArrowLeft :size="15" aria-hidden="true" />
          {{ generating ? t('reports.viewer.stopAndBack') : t('reports.viewer.back') }}
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
          <!-- While a report streams, Stop sits above it (Chat's Charcoal Stop). -->
          <div v-if="generating" class="gen-bar">
            <button ref="stopBtn" type="button" class="stop-gen" @click="stopGeneration">
              <Square :size="13" aria-hidden="true" />
              {{ t('reports.form.stop') }}
            </button>
          </div>
          <img v-if="current.cover_image" class="cover-img" :src="current.cover_image" alt="" />
          <p v-if="imagesStatusText" class="images-status">{{ imagesStatusText }}</p>
          <header v-if="reportHeading || current.id" class="report-head">
            <div class="report-head-text">
              <h2 v-if="reportHeading" class="report-title-h">{{ reportHeading }}</h2>
              <p v-if="metaParts.length" class="report-meta">
                <span v-for="(part, i) in metaParts" :key="i" class="meta-part">{{ part }}</span>
              </p>
            </div>
            <div v-if="current.id" class="report-actions">
              <button type="button" class="pdf-btn" @click="copyReport">
                <Check v-if="reportCopied" :size="15" />
                <Copy v-else :size="15" />
                {{ reportCopied ? t('reports.viewer.copied') : t('reports.viewer.copy') }}
              </button>
              <button type="button" class="pdf-btn" :disabled="pdfLoading" @click="downloadPdf">
                <Loader2 v-if="pdfLoading" :size="15" class="spin" />
                <FileDown v-else :size="15" />
                {{ pdfLoading ? t('reports.viewer.pdfPreparing') : t('reports.viewer.pdf') }}
              </button>
            </div>
          </header>
          <p v-if="pdfError" class="pdf-error">{{ errorText(pdfError) }}</p>
          <!-- The report model reads all sources before writing its first word (40 to
               110 seconds), so the wait says what is happening. Its request and stage
               line stay above the text as it streams, until the report is saved. -->
          <ReportProgress
            v-if="generating && !current.id"
            :type="current.report_type"
            :country="current.country"
            :theme="current.theme || ''"
            :date-from="current.date_from || ''"
            :date-to="current.date_to || ''"
            :language="current.language"
            :started="!!current.content"
            :reading="current.reading"
          />
          <!-- The report body is in the report's language, whatever the interface's. -->
          <article
            class="report-content"
            :lang="reportLang"
            v-html="
              injectSectionImages(
                renderMarkdown(shown.content, shown.sources),
                current.section_images,
              )
            "
          ></article>
          <p v-if="current.stopped" class="stopped-note" role="status">
            {{ t('reports.viewer.stopped') }}
          </p>
          <!-- Chat's error: hairline border, the alert icon and "Try again" in place;
               the form still holds what was asked for. -->
          <div v-if="genError" class="error-banner">
            <AlertCircle :size="16" class="error-icon" aria-hidden="true" />
            <span class="error-text">{{ errorText(genError) }}</span>
            <button
              v-if="!generating && form.country"
              type="button"
              class="retry-btn"
              @click="generate"
            >
              <RotateCcw :size="14" aria-hidden="true" />
              {{ t('common.tryAgain') }}
            </button>
          </div>
          <SourceList v-if="shown.sources" :sources="shown.sources" />
        </div>
        <!-- Nothing open: the new-report form, then the user's series to pick up. -->
        <div v-else class="report-compose">
          <form class="report-form" @submit.prevent="generate">
            <h2 ref="formTitle" class="form-title" tabindex="-1">{{ t('reports.form.title') }}</h2>
            <p class="form-lede">{{ t('reports.empty.lede') }}</p>

            <div class="form-card">
              <fieldset class="type-field" :disabled="generating">
                <legend class="field-label">{{ t('reports.form.type') }}</legend>
                <div class="type-grid">
                  <label
                    v-for="rt in REPORT_TYPES"
                    :key="rt.value"
                    :class="['type-option', { selected: form.report_type === rt.value }]"
                  >
                    <input
                      v-model="form.report_type"
                      type="radio"
                      name="report-type"
                      class="type-radio"
                      :value="rt.value"
                    />
                    <span class="type-name">{{ reportTypeLabel(rt.value, t) }}</span>
                    <span class="type-desc">{{ t('reports.typeDescriptions.' + rt.value) }}</span>
                  </label>
                </div>
              </fieldset>

              <div class="field-grid">
                <label class="field">
                  <span class="field-label">{{ t('reports.form.country') }}</span>
                  <select v-model="form.country" required :disabled="generating">
                    <option value="" disabled>{{ t('reports.form.countryPlaceholder') }}</option>
                    <option v-for="c in countries" :key="c" :value="c">{{ c }}</option>
                  </select>
                </label>
                <label class="field">
                  <span class="field-label">{{ t('reports.form.sector') }}</span>
                  <select v-model="form.theme" :disabled="generating">
                    <option value="">{{ t('reports.form.allSectors') }}</option>
                    <option v-for="th in themes" :key="th" :value="th">
                      {{ sectorLabel(th, t) }}
                    </option>
                  </select>
                </label>
              </div>

              <div class="field-grid field-grid--period">
                <label class="field">
                  <span class="field-label">{{ t('reports.form.from') }}</span>
                  <DateField
                    v-model="form.date_from"
                    :min="minDate"
                    :max="form.date_to || maxDate"
                    :disabled="generating"
                  />
                </label>
                <label class="field">
                  <span class="field-label">{{ t('reports.form.to') }}</span>
                  <DateField
                    v-model="form.date_to"
                    :min="form.date_from || minDate"
                    :max="maxDate"
                    :disabled="generating"
                  />
                </label>
                <label class="field field--language">
                  <span class="field-label">{{ t('reports.form.language') }}</span>
                  <!-- The report's own language, named in the interface language. -->
                  <select v-model="form.language" :disabled="generating">
                    <option value="en">{{ t('lang.names.en') }}</option>
                    <option value="tr">{{ t('lang.names.tr') }}</option>
                  </select>
                </label>
              </div>

              <div class="form-foot">
                <button
                  type="submit"
                  class="generate-btn"
                  :disabled="!form.country || generating"
                  :aria-describedby="optionsError || !form.country ? 'generate-hint' : undefined"
                >
                  <FileText :size="16" aria-hidden="true" />
                  {{ t('reports.form.generate') }}
                </button>
                <!-- Why Generate is off, read with the button. -->
                <p v-if="optionsError" id="generate-hint" class="form-hint">
                  {{ t('reports.form.optionsError') }}
                </p>
                <p v-else-if="!countries.length" id="generate-hint" class="form-hint">
                  {{ t('reports.form.loadingCountries') }}
                </p>
                <p v-else-if="!form.country" id="generate-hint" class="form-hint">
                  {{ t('reports.form.chooseCountry') }}
                </p>
              </div>
            </div>
          </form>
        </div>
      </main>
    </div>
    <CitePreview :root="viewer" />
    <UndoToast
      :message="toastMessage"
      :kind="pendingDelete ? 'undo' : 'error'"
      :action-label="pendingDelete ? t('reports.toast.undo') : ''"
      :focus-action="!!pendingDelete"
      :focus-key="pendingDelete ? pendingDelete.id : null"
      @action="undoDelete"
      @dismiss="notice = ''"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, onActivated, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  FileText,
  Trash2,
  Loader2,
  AlertCircle,
  FileDown,
  Copy,
  Check,
  ArrowLeft,
  Square,
  Plus,
  RotateCcw,
} from 'lucide-vue-next'
import AppTopbar from '../components/AppTopbar.vue'
import SourceList from '../components/SourceList.vue'
import UndoToast from '../components/UndoToast.vue'
import CitePreview from '../components/CitePreview.vue'
import ReportProgress from '../components/ReportProgress.vue'
import DateField from '../components/DateField.vue'
import { useUndoableDelete } from '../utils/undoableDelete.js'
import { renderMarkdown } from '../utils/renderMarkdown.js'
import { renumberCitations, numberByFirstAppearance } from '../utils/renumberCitations.js'
import { injectSectionImages } from '../utils/reportImages.js'
import { revealSource, returnToCite } from '../utils/sources.js'
import { parseSSE } from '../utils/parseSSE.js'
import { getReportOptions, listReports, getReport, deleteReport } from '../utils/reportsApi.js'
import { REPORT_TYPES, reportTypeLabel, sectorLabel } from '../utils/reportTypes.js'
import { splitReportTitle, formatPeriod } from '../utils/reportTitle.js'
import { copyWithSources } from '../utils/citationCopy.js'
import { localIsoDay, minReportDate, maxReportDate } from '../utils/reportDateBounds.js'
import { handleSessionExpired } from '../utils/authStore.js'
import { errorFromResponse, errorMessage } from '../utils/errorMessage.js'
import { normalizeLocale } from '../i18n/locale.js'

// Two languages meet on this page. The interface language (the selector) names
// everything the app says: labels, buttons, statuses, errors, the type, sector and
// period lines around a report. The report's own language (its `language`) holds
// what was generated: the body, its headings and charts, and the copy and PDF taken
// away. Messages and errors are kept as keys or error objects and translated when
// rendered, so a language switch reaches all of them.
const { t, te, locale } = useI18n()

// Prod retains ~1 year of data; clamp the date pickers to [one year ago, today]
// so a user can't pick a window with no indexed reports (or a future date).
const minDate = computed(() => minReportDate(new Date()))
const maxDate = computed(() => maxReportDate())

const countries = ref([])
const themes = ref([])
const optionsError = ref(false)

const reports = ref([])
const loadingList = ref(false)
const openingId = ref(null) // saved report being fetched for the viewer
const listLoaded = ref(false)
// The form was asked for (New report): phones show it, not the list.
const composing = ref(false)
const route = useRoute()
const router = useRouter()

// The report language starts as the interface language (still changeable).
const form = ref({
  report_type: 'situation',
  country: '',
  theme: '',
  date_from: '',
  date_to: '',
  language: locale.value,
})

const current = ref(null) // a saved report as toCurrent() shapes it, or the one streaming

// A report still streaming carries the model's retrieval numbers ([15], [16]); the
// server renumbers them by first appearance when it saves. Show that numbering
// until the stored copy has replaced the streamed text, so the citations never
// change. `generating` stays on after "saved" sets the id, while the stored copy
// loads; renumbering it again is harmless (already 1..n by first appearance). A
// stopped, unsaved report keeps the numbering too.
const shown = computed(() => {
  const c = current.value
  if (!c) return { content: '', sources: null }
  if (c.id && !generating.value) return { content: c.content, sources: c.sources }
  if (c.sources) return renumberCitations(c.content, c.sources)
  return { content: numberByFirstAppearance(c.content), sources: null }
})

// The viewer's copy of a saved report.
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
    cover_image: rep.cover_image,
    section_images: rep.section_images,
  }
}
const generating = ref(false)
// { key } for the view's own messages, { err } for a failed request (its code,
// status) with `fallback` naming the message when the code has none of its own.
const genError = ref(null)
const viewer = ref(null)
const controller = ref(null)

const pdfLoading = ref(false)
const pdfError = ref(null)

function errorText(problem) {
  if (!problem) return ''
  if (problem.key) return t(problem.key)
  const { err, fallback } = problem
  return err && err.code && te(`errors.${err.code}`) ? errorMessage(err, t) : t(fallback)
}

// While a report's images are drawn: { stage: 'cover' } or { stage: 'section', heading }.
const imagesStatusText = computed(() => {
  const s = current.value && current.value.imagesStatus
  if (!s) return ''
  return s.stage === 'cover'
    ? t('reports.viewer.imagesCover')
    : t('reports.viewer.imagesSection', { heading: s.heading })
})

// The open report's language, for the body's lang attribute.
const reportLang = computed(() => (current.value && current.value.language) || undefined)

// Default period: the last three months, in local calendar days (like the bounds).
function setDefaultDates() {
  const to = new Date()
  const from = new Date()
  from.setMonth(from.getMonth() - 3)
  form.value.date_from = localIsoDay(from)
  form.value.date_to = localIsoDay(to)
}

// A report is named from its own fields (country, theme, dates), in the interface
// language. The stored title ("[Type —] Country · Sector · period", English labels)
// is only the fallback for a row that lacks them.
function shownCountry(r) {
  return (r && r.country) || splitReportTitle(r && r.title).heading
}

// The sector in the interface language; none ("All sectors") shows nothing.
function shownSector(r) {
  if (r && r.theme) return sectorLabel(r.theme, t)
  const { sector } = splitReportTitle(r && r.title)
  return sector && sector !== 'All sectors' ? sector : ''
}

function savedName(r) {
  const sector = shownSector(r)
  return sector ? `${shownCountry(r)} · ${sector}` : shownCountry(r)
}

// The type in full ("Situation Report"), as under the open report's title.
function savedType(r) {
  return reportTypeLabel(r.report_type, t)
}

// The saved list's short type ("Situation", "Needs"); the full name is read out.
function savedTypeShort(r) {
  return reportTypeLabel(r.report_type, (key) =>
    t(key.replace('reports.types.', 'reports.typesShort.')),
  )
}

// A list row's tooltip, the full name of a row that may be cut off: the stored
// title in English (unchanged), the row's own name and period otherwise, so a
// Turkish row is not explained in English.
function rowTitle(r) {
  if (locale.value === 'en') return r.title
  return [savedName(r), savedPeriod(r), languageLabel(r)].filter(Boolean).join(' · ')
}

// A report's language as stored: a language tag ("en", "tr", "pt-BR"). Reports saved
// without one (the column is nullable), or with anything that is not a tag, show no
// language rather than a wrong one.
const LANGUAGE_TAG = /^[a-z]{2,3}(-[a-z0-9]{2,8})*$/i
function reportLanguage(r) {
  const code = typeof r.language === 'string' ? r.language.trim() : ''
  return LANGUAGE_TAG.test(code) ? code : null
}

// "Report language: Turkish" / "Rapor dili: Türkçe": the language named in the
// interface language (Intl.DisplayNames), or by its code where the browser has no name.
function languageLabel(r) {
  const code = reportLanguage(r)
  if (!code) return ''
  let name = code
  try {
    name = new Intl.DisplayNames([locale.value], { type: 'language' }).of(code) || code
  } catch {
    // An engine without DisplayNames, or a tag it rejects: the code names it.
  }
  return t('reports.saved.language', { name })
}

// A single day in a list line: day.month.year in both languages.
function shownDay(iso) {
  return formatPeriod(iso)
}

// Each delete button names its report: a list of identical "Delete report"
// buttons does not say which one a screen-reader user is about to remove.
function deleteLabel(r) {
  const period = savedPeriod(r)
  const params = { name: savedName(r), type: savedType(r), period }
  return period ? t('reports.saved.deleteWithPeriod', params) : t('reports.saved.delete', params)
}

// Periods read "17.11.2025 - 17.11.2026" wherever a saved report is named. A report
// with only an end date reads "to 17.11.2026".
function savedPeriod(r) {
  if (r && r.date_from && r.date_to) return formatPeriod(`${r.date_from} – ${r.date_to}`)
  if (r && r.date_to) return t('reports.saved.until', { date: shownDay(r.date_to) })
  return formatPeriod(splitReportTitle(r && r.title).period)
}

// Copy the report text with its numbered Sources list (the PDF stays separate).
const reportCopied = ref(false)
let copiedTimer = null
async function copyReport() {
  if (!current.value) return
  // What is copied is the report: its Sources label is in the report's language.
  const ok = await copyWithSources(current.value.content, current.value.sources, {
    lang: normalizeLocale(current.value.language) || 'en',
  })
  if (!ok) {
    showNotice('reports.notices.copy')
    return
  }
  reportCopied.value = true
  clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => (reportCopied.value = false), 1500)
}

// The open report's heading: its country (the whole stored title if it has none).
const reportHeading = computed(() =>
  current.value && current.value.title ? shownCountry(current.value) : '',
)
// Type · sector · period, each kept whole: the line only wraps between parts,
// and a part carries its leading "·" so no separator is left at a line end.
// Under the report title, one per line: its type, its sector unless it covers all
// sectors, and its period (17.11.2025 - 17.11.2026).
const metaParts = computed(() => {
  if (!current.value || !current.value.title) return []
  return [
    reportTypeLabel(current.value.report_type, t),
    shownSector(current.value),
    savedPeriod(current.value),
  ].filter(Boolean)
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

// App.vue keeps this screen alive while another one is open, and a report keeps
// streaming meanwhile. The URL and the tab title then belong to that other screen:
// away from this screen's path, it neither reads nor writes them, and on its
// return it opens the report a link names or puts the open report back in the URL.
const ownPath = route.path
const onScreen = () => route.path === ownPath
let firstActivation = true
onActivated(() => {
  if (firstActivation) {
    firstActivation = false
    return
  }
  const id = route.query.report
  if (id) followRoute(id)
  // The router names the tab after each navigation, this restored URL included.
  const restored = !id && current.value && current.value.id ? syncUrl(current.value.id) : null
  Promise.resolve(restored).then(applyTitle)
})

// Back/Forward or an edited URL: open the named report, or return to the library.
watch(
  () => route.query.report,
  (id) => {
    if (onScreen()) followRoute(id)
  },
  { immediate: true },
)

function followRoute(id) {
  if (!id) {
    if (current.value && !generating.value) current.value = null
    return
  }
  if (id === openingId.value || (current.value && current.value.id === id)) return
  openReport(id, { fromRoute: true })
}

// Tab title names the open report ("Afghanistan · Situation Report · Humanitaria").
// The locale is a source too: on a language switch the router re-applies the
// route's own title synchronously, and this watcher runs after it.
function applyTitle() {
  const heading = reportHeading.value
  document.title = heading
    ? t('reports.docTitle', { heading, type: reportTypeLabel(current.value?.report_type, t) })
    : `${t('titles.reports')} · Humanitaria`
}
watch(
  () => [reportHeading.value, current.value && current.value.report_type, locale.value],
  () => {
    if (onScreen()) applyTitle()
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
    showNotice('reports.notices.load')
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
  if (!onScreen()) return Promise.resolve()
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
  composing.value = false
  openingId.value = id
  if (!fromRoute) syncUrl(id, { push: true })
  try {
    const rep = await getReport(id)
    current.value = toCurrent(rep)
    genError.value = null
    nextTick(() => {
      if (viewer.value) viewer.value.scrollTop = 0
    })
  } catch (e) {
    console.error('Failed to open report:', e)
    showNotice('reports.notices.open')
    if (!current.value || current.value.id !== id) syncUrl(null)
  } finally {
    if (openingId.value === id) openingId.value = null
  }
}

// Errors for list actions, shown in the same toast as Undo (they used to reach
// only the console). Cleared after a few seconds or by the dismiss button. Holds
// a message key, translated when shown.
const notice = ref('')
let noticeTimer = null
function showNotice(key) {
  notice.value = key
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
    showNotice('reports.notices.delete')
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
const stopBtn = ref(null)

// The main column holds the open report, else the new-report form. Phones show one
// pane: the library, or the main column once a report or the form is asked for (or
// at once when there is nothing saved to list).
const formTitle = ref(null)
const mainPane = computed(
  () =>
    !!(current.value || openingId.value) ||
    composing.value ||
    (listLoaded.value && !reports.value.length),
)
const showBack = computed(
  () => !!(current.value || openingId.value) || (composing.value && reports.value.length > 0),
)
function backToList() {
  composing.value = false
  if (generating.value) stopAndShowList()
  else if (current.value || openingId.value) closeReport()
}
function openForm() {
  if (generating.value) return
  composing.value = true
  genError.value = null
  form.value.language = locale.value
  // A saved report closes through the URL; an unsaved one (stopped, failed) has none.
  if (current.value) {
    current.value = null
    closeReport()
  }
  nextTick(() => formTitle.value && formTitle.value.focus())
}

const toastMessage = computed(() =>
  pendingDelete.value ? t('reports.toast.deleted') : notice.value ? t(notice.value) : '',
)

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
  pdfError.value = null
  try {
    const url0 = `/reports/${current.value.id}/pdf`
    const res = await fetch(url0, { credentials: 'include' })
    if (!res.ok) {
      if (res.status === 401) {
        handleSessionExpired()
        return
      }
      throw await errorFromResponse(res, url0)
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
    pdfError.value = { err: e, fallback: 'reports.viewer.pdfError' }
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
  composing.value = false
  genError.value = null
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
    country: form.value.country,
    theme: form.value.theme || null,
    date_from: form.value.date_from || null,
    date_to: form.value.date_to || null,
    language: form.value.language,
    cover_image: null,
    section_images: null,
    imagesStatus: null,
    reading: null, // { count, sources } once the server says what it reads
  }
  // The form gives way to the report; keyboard focus moves to its Stop button.
  nextTick(() => stopBtn.value && stopBtn.value.focus())
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
      // 409 = per-user report limit, 429 = rate limit: named by the error's code.
      genError.value = {
        err: await errorFromResponse(res, '/reports/stream'),
        fallback: 'reports.errors.generate',
      }
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
              d.stage === 'cover' ? { stage: 'cover' } : { stage: 'section', heading: d.heading }
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
            const d = JSON.parse(sse.data)
            // Before the first word: what the report reads (shown by the waiting state).
            if (d.stage === 'reading') {
              current.value.reading = {
                count: d.count,
                sources: Array.isArray(d.sources) ? d.sources : [],
              }
            }
          } catch (e) {}
        } else if (sse.event === 'saved') {
          current.value.imagesStatus = null
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
              current.value = toCurrent(await getReport(rid))
            } catch (e) {}
          }
        } else if (sse.event === 'error') {
          // { code, message }: the code names the message in the interface language.
          let code = null
          try {
            code = JSON.parse(sse.data).code || null
          } catch (e) {}
          genError.value = { err: { code }, fallback: 'reports.errors.stream' }
        }
      }
    }
  } catch (e) {
    if (e?.name === 'AbortError') {
      if (current.value) current.value.stopped = true
    } else {
      console.error('Report stream error:', e)
      genError.value = { key: 'reports.errors.connection' }
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

/* The same rail as Chat's sidebar (Claude's 288px, 8px side padding). */
.reports-aside {
  width: 288px;
  flex-shrink: 0;
  border-right: 1px solid var(--color-border);
  background-color: var(--color-surface-container-low);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: var(--space-3);
  gap: var(--space-5);
}

/* The rail's primary action, as Chat's New chat. */
.new-report-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  width: 100%;
  min-height: 38px;
  padding: 0 var(--space-4);
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition:
    color 0.15s,
    border-color 0.15s;
}
.new-report-btn:hover:not(:disabled) {
  color: var(--color-accent);
  border-color: var(--color-accent);
}
.new-report-btn:disabled {
  color: var(--color-muted);
  cursor: not-allowed;
}
.new-report-btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* The new-report form: the main column's own 680px measure, heading on the ground,
   the controls on one hairline card. */
.report-compose {
  max-width: 680px;
  margin: 0 auto;
}
.form-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--color-text);
  text-wrap: balance;
}
.form-title:focus {
  outline: none;
}
.form-lede {
  margin: var(--space-2) 0 var(--space-5);
  max-width: 56ch;
  font-size: 15px;
  line-height: 1.55;
  color: var(--color-text-secondary);
}
.form-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-5);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
}

.field-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

/* Report type: four described options, a radio group drawn as 10px controls. */
.type-field {
  margin: 0;
  padding: 0;
  border: none;
  min-width: 0;
}
.type-field legend {
  padding: 0;
  margin-bottom: var(--space-2);
}
.type-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
}
.type-option {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  column-gap: 10px;
  row-gap: 3px;
  align-items: start;
  padding: 12px 14px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-lg);
  background-color: var(--color-surface);
  cursor: pointer;
  transition:
    border-color 0.15s,
    background-color 0.15s;
}
.type-option:hover {
  border-color: color-mix(in srgb, var(--color-accent) 55%, var(--color-border-strong));
}
.type-option.selected {
  border-color: var(--color-accent);
  background-color: var(--color-accent-soft);
}
.type-option:has(.type-radio:focus-visible) {
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}
.type-field:disabled .type-option {
  cursor: not-allowed;
}
.type-radio {
  width: 16px;
  height: 16px;
  margin: 2px 0 0;
  accent-color: var(--color-accent);
}
.type-radio:focus-visible {
  outline: none;
}
.type-name {
  font-size: var(--text-sm);
  font-weight: 600;
  line-height: 1.4;
  color: var(--color-text);
}
.type-desc {
  grid-column: 2;
  font-size: 12.5px;
  line-height: 1.45;
  color: var(--color-text-secondary);
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4) var(--space-3);
}
.field-grid--period {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.field select {
  width: 100%;
  min-height: 40px;
  padding: 8px 12px;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-text);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-lg);
  outline: none;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.field select:focus {
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}

.form-foot {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}
.generate-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: 40px;
  padding: 0 20px;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-on-accent);
  background-color: var(--color-accent-container);
  border: none;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition:
    background-color 0.2s,
    transform 0.15s;
}
.generate-btn:hover:not(:disabled) {
  background-color: color-mix(in srgb, var(--color-accent-container) 86%, #000);
}
.generate-btn:active:not(:disabled) {
  transform: scale(0.98);
}
.generate-btn:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
/* Disabled reads as off in both themes: a neutral shelf fill, not a faded teal. */
.generate-btn:disabled {
  color: var(--color-muted);
  background-color: var(--color-surface-container-high);
  cursor: not-allowed;
}

/* Stop while a report streams: Chat's Charcoal Stop, above the report. */
.gen-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--space-4);
}
.stop-gen {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 36px;
  padding: 0 16px;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-on-tertiary);
  background-color: var(--color-tertiary);
  border: none;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: background-color 0.15s;
}
.stop-gen:hover {
  background-color: var(--color-text-secondary);
}
.stop-gen:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
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
  padding: 10px var(--space-3);
  display: flex;
  flex-direction: column;
  gap: 1px;
}
/* Country, then the sector: both whole, wrapping rather than cut off. */
.saved-name {
  font-size: var(--text-sm);
  font-weight: 600;
  line-height: 1.35;
  color: var(--color-text);
  overflow-wrap: anywhere;
}
.saved-item.active .saved-name {
  color: var(--color-accent);
}
.saved-sector {
  font-size: 13px;
  line-height: 1.35;
  color: var(--color-text-secondary);
  overflow-wrap: anywhere;
}
.saved-period {
  white-space: nowrap;
}
/* The report's language code: the meta line's own quiet text, in every row shape. */
.saved-lang {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 400;
  color: var(--color-text-secondary);
  white-space: nowrap;
}
/* Short type and language, then the period on its own line, in Geist Mono. */
.saved-meta {
  display: flex;
  flex-direction: column;
  margin-top: 3px;
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.5;
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

.report-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: var(--space-6) var(--space-8);
}

/* The reading column: about 75 characters of 15px Geist, whatever the window width. */
.report-column {
  max-width: 680px;
  margin: 0 auto;
  font-size: var(--text-base);
}
.report-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3) var(--space-4);
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-5);
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
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1.12;
  letter-spacing: -0.025em;
  color: var(--color-text);
  text-wrap: balance;
  margin: 0;
}
.meta-part {
  white-space: nowrap;
}
.report-meta {
  display: flex;
  flex-direction: column;
  row-gap: 2px;
  margin: 10px 0 0;
  font-family: var(--font-body);
  font-size: 13px;
  line-height: 1.45;
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
/* A chart is a panel of its own: hairline frame, card radius, room around it. */
.report-content :deep(.section-img) {
  display: block;
  width: 100%;
  margin: 0.9em 0 1.4em;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
}

/* The actions sit on their own row
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
  border-radius: var(--radius-full);
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

/* Report text: Geist at 15px / 1.65. Headings sit closer to the text they open than to
   the text before them; figures in tables line up. */
.report-content {
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.65;
  color: var(--color-text);
}
.report-content :deep(h1) {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  letter-spacing: -0.02em;
  margin: 0 0 0.5em;
}
.report-content :deep(h2) {
  font-family: var(--font-display);
  font-size: 1.1875rem;
  font-weight: 650;
  line-height: 1.3;
  letter-spacing: -0.015em;
  text-wrap: balance;
  margin: 2.1em 0 0.5em;
}
.report-content :deep(h2:first-child) {
  margin-top: 0;
}
.report-content :deep(h3) {
  font-size: var(--text-base);
  font-weight: 650;
  margin: 1.5em 0 0.35em;
}
.report-content :deep(p) {
  margin: 0 0 0.9em;
}
.report-content :deep(ul),
.report-content :deep(ol) {
  margin: 0.3em 0 1em;
  padding-left: 1.25em;
}
.report-content :deep(li) {
  margin-bottom: 0.4em;
}
.report-content :deep(li::marker) {
  color: var(--color-muted);
}
/* Tables: ruled rows on the page ground, the header on Cloud Ground. */
.report-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.8em 0 1.4em;
  font-size: var(--text-sm);
  font-variant-numeric: tabular-nums;
}
.report-content :deep(th),
.report-content :deep(td) {
  border-bottom: 1px solid var(--color-border);
  padding: 8px 12px;
  text-align: left;
  vertical-align: top;
}
.report-content :deep(th) {
  background-color: var(--color-surface-container-low);
  border-bottom-color: var(--color-border-strong);
  font-weight: 600;
  color: var(--color-text-secondary);
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
  border-radius: var(--radius-full);
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
  .reports-body.has-main .reports-aside {
    display: none;
  }
  .reports-body:not(.has-main) .report-main {
    display: none;
  }
  .report-main {
    padding: var(--space-4);
  }
  .back-to-list {
    display: inline-flex;
  }
  .type-grid,
  .field-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .field-grid--period {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .field--language {
    grid-column: 1 / -1;
  }
  .form-card {
    padding: var(--space-4);
  }
  .generate-btn {
    width: 100%;
  }
}
</style>

