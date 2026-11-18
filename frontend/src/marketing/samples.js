// The landing's Syria samples in each interface language: one answer the chat
// pipeline gave and one situation report, both generated verbatim by
// scripts/generate_landing_answer.py and scripts/generate_landing_report.py.
// Both languages are bundled: the files are small, and a language switch must
// never wait on a fetch or show an empty card.
import answerEn from './data/syriaAnswer.en.json'
import answerTr from './data/syriaAnswer.tr.json'
import reportEn from './data/meReport.en.json'
import reportTr from './data/meReport.tr.json'
import { passage } from './landingKit.js'

const ANSWERS = { en: answerEn, tr: answerTr }
const REPORTS = { en: reportEn, tr: reportTr }

// The stretch of each answer the workflow card quotes: its first figure and the
// sentence after it, with their own citations ([1] and [2]).
const PASSAGES = {
  en: ['An estimated 1,803,441', 'reduced or halted'],
  tr: ["Suriye'de 8 Aralık 2024", 'geri dönüş yapmıştır'],
}

export const sampleAnswer = (locale) => ANSWERS[locale] ?? ANSWERS.en

export const sampleReport = (locale) => REPORTS[locale] ?? REPORTS.en

export function samplePassage(locale) {
  const key = ANSWERS[locale] ? locale : 'en'
  return passage(ANSWERS[key].parts, ...PASSAGES[key])
}
