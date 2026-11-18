<template>
  <div class="reports-app">
    <AppTopbar :context="t('reports.topbar')" />

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
          {{ t('reports.newReport') }}
        </button>
        <form v-else class="report-form" @submit.prevent="generate">
          <h2 ref="formTitle" class="form-title" tabindex="-1">{{ t('reports.form.title') }}</h2>

          <label class="field">
            <span>{{ t('reports.form.type') }}</span>
            <select v-model="form.report_type" :disabled="generating">
              <option v-for="rt in REPORT_TYPES" :key="rt.value" :value="rt.value">
                {{ reportTypeLabel(rt.value, t) }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>{{ t('reports.form.country') }}</span>
            <select v-model="form.country" required :disabled="generating">
              <option value="" disabled>{{ t('reports.form.countryPlaceholder') }}</option>
              <option v-for="c in countries" :key="c" :value="c">{{ c }}</option>
            </select>
          </label>

          <label class="field">
            <span>{{ t('reports.form.sector') }}</span>
            <select v-model="form.theme" :disabled="generating">
              <option value="">{{ t('reports.form.allSectors') }}</option>
              <option v-for="th in themes" :key="th" :value="th">{{ sectorLabel(th, t) }}</option>
            </select>
          </label>

          <div class="field-row">
            <label class="field">
              <span>{{ t('reports.form.from') }}</span>
              <input
                v-model="form.date_from"
                type="date"
                :min="minDate"
                :max="form.date_to || maxDate"
                :disabled="generating"
              />
            </label>
            <label class="field">
              <span>{{ t('reports.form.to') }}</span>
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
            <span>{{ t('reports.form.language') }}</span>
            <!-- The report's own language, named in the interface language. -->
            <select v-model="form.language" :disabled="generating">
              <option value="en">{{ t('lang.names.en') }}</option>
              <option value="tr">{{ t('lang.names.tr') }}</option>
            </select>
          </label>

          <!-- "Run next period": the new report continues a saved one and opens
               with what changed since then. -->
          <div v-if="continuation && !generating" class="continues" role="status">
            <template v-if="continuesSeries">
              <i18n-t keypath="reports.continues.series" tag="p" scope="global">
                <template #name>
                  <strong>{{ savedName(continuation.report) }}</strong>
                </template>
                <template #period>
                  <span class="continues-period">{{ savedPeriod(continuation.report) }}</span>
                </template>
              </i18n-t>
              <p v-if="continuationNotes.endClamped" class="form-hint">
                {{ t('reports.continues.endClamped') }}
              </p>
              <p v-if="continuationNotes.startClamped" class="form-hint">
                {{ t('reports.continues.startClamped', { date: shownDay(minDate) }) }}
              </p>
            </template>
            <i18n-t v-else keypath="reports.continues.differs" tag="p" scope="global">
              <template #name>
                <strong>{{ savedName(continuation.report) }}</strong>
              </template>
            </i18n-t>
            <button type="button" class="continues-clear" @click="continuation = null">
              {{ continuesSeries ? t('reports.continues.clear') : t('common.dismiss') }}
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
            {{ t('reports.form.stop') }}
          </button>
          <button
            v-else
            ref="generateBtn"
            type="submit"
            class="generate-btn"
            :disabled="!form.country"
          >
            <FileText :size="16" />
            {{ t('reports.form.generate') }}
          </button>

          <p v-if="optionsError" class="form-hint">{{ t('reports.form.optionsError') }}</p>
          <p v-else-if="!countries.length" class="form-hint">
            {{ t('reports.form.loadingCountries') }}
          </p>
          <p v-else-if="!form.country && !generating" class="form-hint">
            {{ t('reports.form.chooseCountry') }}
          </p>
        </form>

        <div class="saved">
          <h3 class="saved-title-h">{{ t('reports.saved.title') }}</h3>
          <p v-if="generating" class="form-hint">
            {{ t('reports.saved.waitWhileGenerating') }}
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
                  :title="rowTitle(e.report)"
                  :aria-disabled="generating ? 'true' : undefined"
                  @click="openReport(e.report.id)"
                >
                  <span class="saved-name">{{ savedName(e.report) }}</span>
                  <span class="saved-meta">
                    <!-- The report's language as its code, so an English and a Turkish
                         report with the same settings can be told apart. The "·" is
                         glued to the type by a no-break space, so a long type name
                         wraps between its words and no line starts with a separator. -->
                    <span
                      >{{ savedType(e.report)
                      }}<span v-if="reportLanguage(e.report)" class="saved-lang"
                        >{{ '\u00a0· '
                        }}<span class="saved-lang-code" aria-hidden="true">{{
                          reportLanguage(e.report).toUpperCase()
                        }}</span
                        ><span class="sr-only">{{ languageLabel(e.report) }}</span></span
                      ></span
                    >
                    <span v-if="savedPeriod(e.report)" class="saved-period">{{
                      savedPeriod(e.report)
                    }}</span>
                  </span>
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
                    <!-- Type, then count and language kept together: the line can
                         only break after "Type ·". The period has its own line. -->
                    <span class="saved-meta"
                      ><span
                        >{{ savedType(e.latest) }}{{ '\u00a0· '
                        }}<span class="saved-count"
                          >{{ t('reports.saved.count', { n: e.reports.length }, e.reports.length)
                          }}<span v-if="reportLanguage(e.latest)" class="saved-lang"
                            >{{ '\u00a0· '
                            }}<span class="saved-lang-code" aria-hidden="true">{{
                              reportLanguage(e.latest).toUpperCase()
                            }}</span
                            ><span class="sr-only">{{ languageLabel(e.latest) }}</span></span
                          ></span
                        ></span
                      ><span v-if="e.latest.date_to" class="saved-period">{{
                        t('reports.saved.until', { date: shownDay(e.latest.date_to) })
                      }}</span></span
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
                      :title="rowTitle(r)"
                      :aria-disabled="generating ? 'true' : undefined"
                      @click="openReport(r.id)"
                    >
                      <span class="saved-name saved-period-name"
                        >{{ savedPeriod(r) || t('reports.saved.noPeriod')
                        }}<span v-if="reportLanguage(r)" class="saved-lang"
                          >{{ ' · '
                          }}<span class="saved-lang-code" aria-hidden="true">{{
                            reportLanguage(r).toUpperCase()
                          }}</span
                          ><span class="sr-only">{{ languageLabel(r) }}</span></span
                        ></span
                      >
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
          <p v-else class="form-hint">{{ t('reports.saved.empty') }}</p>
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
          <img v-if="current.cover_image" class="cover-img" :src="current.cover_image" alt="" />
          <p v-if="imagesStatusText" class="images-status">{{ imagesStatusText }}</p>
          <header v-if="titleParts.heading || current.id" class="report-head">
            <div class="report-head-text">
              <h2 v-if="titleParts.heading" class="report-title-h">{{ titleParts.heading }}</h2>
              <p v-if="metaParts.length" class="report-meta">
                <span v-for="(part, i) in metaParts" :key="i" class="meta-part">{{ part }}</span>
              </p>
              <template v-if="comparedWith">
                <p v-if="comparedWith.deleted" class="report-compared">
                  {{ t('reports.viewer.comparedDeleted') }}
                </p>
                <i18n-t
                  v-else
                  keypath="reports.viewer.comparedWith"
                  tag="p"
                  class="report-compared"
                  scope="global"
                >
                  <template #link>
                    <button
                      type="button"
                      class="report-compared-link"
                      @click="openReport(comparedWith.id)"
                    >
                      {{ comparedWith.period || t('reports.viewer.previousReport') }}
                    </button>
                  </template>
                </i18n-t>
              </template>
              <!-- A series is implicit: a report made as a one-off can sit after an
                   earlier period it was never compared with. Say so. -->
              <i18n-t
                v-if="notComparedWith"
                keypath="reports.viewer.notComparedWith"
                tag="p"
                class="report-compared"
                scope="global"
              >
                <template #link>
                  <button
                    type="button"
                    class="report-compared-link"
                    @click="openReport(notComparedWith.id)"
                  >
                    {{ savedPeriod(notComparedWith) || t('reports.viewer.earlierPeriod') }}
                  </button>
                </template>
              </i18n-t>
              <!-- An older period links forward instead of offering "Run next period",
                   which would continue a different (newer) report. -->
              <i18n-t
                v-if="continuedBy"
                keypath="reports.viewer.continuedBy"
                tag="p"
                class="report-compared"
                scope="global"
              >
                <template #link>
                  <button
                    type="button"
                    class="report-compared-link"
                    @click="openReport(continuedBy.id)"
                  >
                    {{ savedPeriod(continuedBy) || t('reports.viewer.laterReport') }}
                  </button>
                </template>
              </i18n-t>
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
                {{ t('reports.viewer.runNext') }}
              </button>
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
            :compared-period="current.comparedPeriod || ''"
            :started="!!current.content"
            :checking="!!current.checking"
            :reading="current.reading"
            :stats="current.computed"
          />
          <!-- The report body is in the report's language, whatever the interface's. -->
          <article
            class="report-content"
            :lang="reportLang"
            v-html="
              injectComparisonNote(
                injectSectionImages(
                  renderMarkdown(shown.content, shown.sources),
                  current.section_images,
                ),
                comparisonNote(
                  {
                    checking: current.checking,
                    period: current.comparedPeriod,
                    removed: current.checkRemoved,
                  },
                  t,
                  locale,
                ),
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
        <!-- Nothing open: Chat's empty pattern (left-aligned promise, coverage line,
             hairline rows), with the user's series as the starting points. -->
        <div v-else class="report-empty">
          <div class="empty-inner">
            <h2 class="empty-title">{{ t('reports.empty.title') }}</h2>
            <p class="empty-lede">{{ t('reports.empty.lede') }}</p>
            <template v-if="emptyRows.length">
              <p class="empty-pick">
                {{
                  emptyRows[0].series
                    ? t('reports.empty.pickSeries')
                    : t('reports.empty.pickRecent')
                }}
              </p>
              <ul
                class="empty-list"
                :aria-label="
                  emptyRows[0].series
                    ? t('reports.empty.seriesLabel')
                    : t('reports.empty.recentLabel')
                "
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
      :action-label="pendingDelete ? t('reports.toast.undo') : ''"
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
import ReportProgress from '../components/ReportProgress.vue'
import { useUndoableDelete } from '../utils/undoableDelete.js'
import { renderMarkdown } from '../utils/renderMarkdown.js'
import { renumberCitations, numberByFirstAppearance } from '../utils/renumberCitations.js'
import { injectSectionImages } from '../utils/reportImages.js'
import { comparisonNote, injectComparisonNote } from '../utils/comparisonNote.js'
import { revealSource, returnToCite } from '../utils/sources.js'
import { parseSSE } from '../utils/parseSSE.js'
import { getReportOptions, listReports, getReport, deleteReport } from '../utils/reportsApi.js'
import { REPORT_TYPES, reportTypeLabel, sectorLabel } from '../utils/reportTypes.js'
import { splitReportTitle, formatPeriod } from '../utils/reportTitle.js'
import { groupSeries, newerInSeries, olderInSeries, seriesKey } from '../utils/reportSeries.js'
import { nextPeriod } from '../utils/nextPeriod.js'
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

// Titles carry "[Type —] Country · Sector · period"; the country leads, the rest
// moves to a small meta line (type as text, not a pill). The stored title is data
// (English labels); the type and sector shown come from the report's codes, in the
// interface language.
function shownSector(r, titleSector) {
  if (!titleSector || titleSector === 'All sectors') return ''
  return r.theme ? sectorLabel(r.theme, t) : titleSector
}

function savedName(r) {
  const { heading, sector } = splitReportTitle(r.title)
  const name = shownSector(r, sector)
  return name ? `${heading} · ${name}` : heading
}

// The type in full ("Situation Report"), as under the open report's title.
function savedType(r) {
  return reportTypeLabel(r.report_type, t)
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

// A single day in a list line: ISO in English as before, day.month.year in Turkish.
function shownDay(iso) {
  return locale.value === 'tr' ? formatPeriod(iso) : iso
}

// Each delete button names its report: a list of identical "Delete report"
// buttons does not say which one a screen-reader user is about to remove.
function deleteLabel(r) {
  const period = savedPeriod(r)
  const params = { name: savedName(r), type: savedType(r), period }
  return period ? t('reports.saved.deleteWithPeriod', params) : t('reports.saved.delete', params)
}

// Periods read "17.11.2025 - 17.11.2026" wherever a saved report is named.
function savedPeriod(r) {
  return formatPeriod(splitReportTitle(r.title).period)
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

const titleParts = computed(() => splitReportTitle(current.value && current.value.title))
// Type · sector · period, each kept whole: the line only wraps between parts,
// and a part carries its leading "·" so no separator is left at a line end.
// Under the report title, one per line: its type, its sector unless it covers all
// sectors, and its period (17.11.2025 - 17.11.2026).
const metaParts = computed(() => {
  if (!current.value || !current.value.title) return []
  const { sector, period } = titleParts.value
  return [
    reportTypeLabel(current.value.report_type, t),
    shownSector(current.value, sector),
    formatPeriod(period),
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
// The locale is a source too: on a language switch the router re-applies the
// route's own title synchronously, and this watcher runs after it.
watch(
  () => [titleParts.value.heading, current.value && current.value.report_type, locale.value],
  ([heading, type]) => {
    document.title = heading
      ? t('reports.docTitle', { heading, type: reportTypeLabel(type, t) })
      : `${t('titles.reports')} · Humanitaria`
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
          ? t('reports.saved.until', { date: shownDay(e.latest.date_to) })
          : ''
        : next.notStarted
          ? t('reports.empty.nextStarts', { date: shownDay(next.startsOn) })
          : t('reports.empty.nextReady', { date: shownDay(next.date_from) })
      return {
        series: true,
        report: e.latest,
        meta: [
          savedType(e.latest),
          t('reports.saved.count', { n: e.reports.length }, e.reports.length),
          when,
        ]
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
  form.value.language = locale.value
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
  // The saved report itself, not its name: the name is translated where it is shown.
  continuation.value = {
    id: rep.id,
    key: seriesKey(rep),
    report: rep,
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
  formOpen.value = true // the form stays put when the report is saved
  // Generate is replaced by Stop; keep keyboard focus on the control that is there.
  nextTick(() => stopBtn.value && stopBtn.value.focus())
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
    computed: null, // { indicators, date_from, date_to } for technical monitoring
    // The period this report is compared with, for the note under "What changed".
    comparedPeriod: continuesSeries.value ? savedPeriod(continuation.value.report) : null,
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
        genError.value = {
          key:
            res.status === 404
              ? 'reports.errors.previousDeleted'
              : 'reports.errors.previousMismatch',
        }
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
            // Next-period reports: the streamed "What changed" is checked before it
            // is saved; the note under its heading says so, then what the check did.
            const d = JSON.parse(sse.data)
            // Before the first word: what the report reads, or which statistics
            // a technical report computed (shown by the waiting state).
            if (d.stage === 'reading') {
              current.value.reading = {
                count: d.count,
                sources: Array.isArray(d.sources) ? d.sources : [],
              }
            } else if (d.stage === 'computed') {
              current.value.computed = {
                indicators: Array.isArray(d.indicators) ? d.indicators : [],
                date_from: d.date_from || null,
                date_to: d.date_to || null,
              }
            } else if (d.stage === 'checking_comparison') {
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

/* The same rail as Chat's sidebar (Claude's 288px, 8px side padding). */
.reports-aside {
  width: 288px;
  flex-shrink: 0;
  border-right: 1px solid var(--color-border);
  background-color: var(--color-surface-container-low);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: var(--space-3) var(--space-2);
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
  font-family: var(--font-body);
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
.saved-period,
.saved-count {
  white-space: nowrap;
}
/* The report's language code: the meta line's own quiet text, in every row shape
   (a period row's name is 12px body text; its code steps down to the meta size). */
.saved-lang {
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 400;
  color: var(--color-text-secondary);
  white-space: nowrap;
}
/* Type, then the period on its own line, as under the open report's title. */
.saved-meta {
  display: flex;
  flex-direction: column;
  font-family: var(--font-body);
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
  font-family: var(--font-body);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.report-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: var(--space-6) var(--space-8);
}

/* Claude's reading column: 736px, whatever the window width. */
.report-column {
  max-width: 736px;
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
  flex-direction: column;
  row-gap: 2px;
  margin: 6px 0 0;
  font-family: var(--font-body);
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
/* Technical-report charts are drawn for each theme; the dark one is hidden here and
   swapped in by the unscoped dark-theme rules at the end of this file. */
.report-content :deep(.section-img--dark) {
  display: none;
}

.report-compared {
  margin: 4px 0 0;
  font-family: var(--font-body);
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

/* Report text reads like Claude's answers: the reading serif at 15px / 21px. */
.report-content {
  font-family: var(--font-serif);
  font-size: 15px;
  line-height: 21px;
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
  font-family: var(--font-body);
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

<style>
/* Dark theme: show the dark-drawn technical-report chart instead of the light one.
   Unscoped because the theme attribute sits on <html>, outside this component; the
   extra :root[data-theme] specificity outranks the scoped display rules above. */
:root[data-theme='dark'] .report-content .section-img--light {
  display: none;
}
:root[data-theme='dark'] .report-content .section-img--dark {
  display: block;
}
</style>
