// The landing's Syria samples in each interface language: one answer the chat
// pipeline gave, one situation report and one indicator monitoring report, all
// generated verbatim by scripts/generate_landing_answer.py and
// scripts/generate_landing_report.py.
// Both languages are bundled: the files are small, and a language switch must
// never wait on a fetch or show an empty card.
import answerEn from './data/syriaAnswer.en.json'
import answerTr from './data/syriaAnswer.tr.json'
import reportEn from './data/meReport.en.json'
import reportTr from './data/meReport.tr.json'
import indicatorsEn from './data/meIndicators.en.json'
import indicatorsTr from './data/meIndicators.tr.json'
import { passage } from './landingKit.js'

const ANSWERS = { en: answerEn, tr: answerTr }
const REPORTS = { en: reportEn, tr: reportTr }
const INDICATORS = { en: indicatorsEn, tr: indicatorsTr }

// The Indicator Table rows each card quotes, by their verbatim indicator name: the
// hero card's headline need, refugee returns and food insecurity, and four others
// (with their dates) for the workflow card, so the two never repeat a row. Values
// are always quoted verbatim. A name the generated translation got wrong is shown
// under the label in RENAMED instead.
const INDICATOR_ROWS = {
  en: {
    hero: [
      'People in need of humanitarian assistance',
      'Refugee returnees to areas of origin (since December 2024)',
      'Acute food insecurity',
    ],
    flow: [
      'Humanitarian Needs and Response Plan funding coverage',
      'Average monthly humanitarian assistance reach',
      'Food assistance beneficiaries',
      'Emergency agriculture assistance reach against annual target',
    ],
  },
  tr: {
    hero: [
      'İnsani yardıma muhtaç nüfus',
      'Geri dönen sığınmacı sayısı',
      'Akut gıda güvensizliği yaşayan nüfus',
    ],
    flow: [
      'İnsani İhtiyaçlar ve Müdahale Planı (HNRP) fonlanma oranı',
      'İnsani yardımla aylık ortalama ulaşılan kişi sayısı',
      'WFP tarafından gıda yardımı ulaştırılan kişi sayısı',
      'Acil tarım yardımı yıllık hedefine ulaşma oranı',
    ],
  },
}

// 'Sığınmacı' (asylum seeker) is the wrong word for refugees returning to Syria; the
// row is the refugee returns from abroad, named as displaced people returning from
// outside the country.
const RENAMED = {
  tr: { 'Geri dönen sığınmacı sayısı': 'Ülke dışından geri dönen yerinden edilmiş kişi sayısı' },
}

// The stretch of each answer the workflow card quotes: its first figure and the
// sentence after it, with their own citations ([1] and [2]).
const PASSAGES = {
  en: ['An estimated 1,803,441', 'reduced or halted'],
  tr: ['Güncel verilere göre', 'geri dönüş yapmıştır'],
}

export const sampleAnswer = (locale) => ANSWERS[locale] ?? ANSWERS.en

export const sampleReport = (locale) => REPORTS[locale] ?? REPORTS.en

export function samplePassage(locale) {
  const key = ANSWERS[locale] ? locale : 'en'
  return passage(ANSWERS[key].parts, ...PASSAGES[key])
}

// One card's rows of the sample indicator report ('hero' or 'flow'), each as
// { indicator, value, asOf }, with only the sources those rows cite.
export function sampleIndicators(locale, card) {
  const key = INDICATORS[locale] ? locale : 'en'
  const report = INDICATORS[key]
  const rows = INDICATOR_ROWS[key][card].map((name) => {
    const row = report.rows.find((r) => r[0] === name)
    return { indicator: RENAMED[key]?.[row[0]] ?? row[0], value: row[1], asOf: row[2] }
  })
  const cited = new Set(rows.flatMap((r) => [...r.value.matchAll(/\[(\d+)\]/g)].map((m) => +m[1])))
  return { ...report, rows, sources: report.sources.filter((s) => cited.has(s.n)) }
}
