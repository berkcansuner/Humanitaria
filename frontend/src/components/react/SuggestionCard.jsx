import { useState, useRef, useEffect, useMemo } from 'react'
import { ChevronLeft, ChevronRight, ArrowRight, X, Check } from 'lucide-react'
import './SuggestionCard.css'

// Each missing query dimension becomes one step (only those with suggestions).
// `chips: false` -> free-text only (with autocomplete); `true` -> chips + text.
const STEP_DEFS = [
  { key: 'country', src: 'countries', chips: false, title: 'Which country would you like information about?', placeholder: 'Enter a country…' },
  { key: 'date', src: 'time_periods', chips: false, title: 'Which time period?', placeholder: 'Enter a time period…' },
  { key: 'theme', src: 'themes', chips: true, title: 'Which topic?', placeholder: 'or enter a topic…' },
]

/**
 * Multi-step suggestion card (React island).
 * Props:
 *   clarification: { suggestions: { countries, time_periods, themes } }
 *   onApply: (values: string[]) => void   // chosen values in step order
 *   onDismiss: () => void
 */
export default function SuggestionCard({ clarification, onApply, onDismiss }) {
  const steps = useMemo(() => {
    const s = clarification?.suggestions || {}
    return STEP_DEFS
      .filter((d) => Array.isArray(s[d.src]) && s[d.src].length)
      .map((d) => ({ key: d.key, title: d.title, placeholder: d.placeholder, chips: d.chips, options: s[d.src] }))
  }, [clarification])

  const [current, setCurrent] = useState(0)
  const [selections, setSelections] = useState({})
  const [custom, setCustom] = useState('')
  const [selecting, setSelecting] = useState(null)
  const [activeMatch, setActiveMatch] = useState(-1)
  const firstOptRef = useRef(null)
  const inputRef = useRef(null)
  const timer = useRef(null)

  // On each step, clear transient state and focus the first chip (or the input
  // when the step has no chips, e.g. country).
  useEffect(() => {
    setCustom('')
    setSelecting(null)
    setActiveMatch(-1)
    const s = steps[current]
    if (s && !s.chips) inputRef.current?.focus({ preventScroll: true })
    else firstOptRef.current?.focus({ preventScroll: true })
  }, [current, steps])

  useEffect(() => () => clearTimeout(timer.current), [])

  if (!steps.length) return null
  const step = steps[current]
  const isLast = current >= steps.length - 1

  // Prefix match (whole label or any word starts with the query) so "s" yields
  // Sudan/Syria/Somalia — not Afghanistan (which only *contains* an "s").
  const q = custom.trim().toLowerCase()
  const matches = q
    ? step.options.filter((o) => {
      const lo = o.toLowerCase()
      return lo.startsWith(q) || lo.split(/\s+/).some((w) => w.startsWith(q))
    })
    : []

  function finalize(next) {
    const values = steps.map((s) => next[s.key]).filter(Boolean)
    if (values.length) onApply(values)
    else onDismiss()
  }
  function advance(next) {
    if (current < steps.length - 1) setCurrent((c) => c + 1)
    else finalize(next)
  }
  function applyValue(v) {
    const val = (v || '').trim()
    if (!val) return null
    const next = { ...selections, [step.key]: val }
    setSelections(next)
    return next
  }
  function prefersReduced() {
    return typeof window !== 'undefined' && window.matchMedia
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }
  // Chip click: briefly flash the "selected" state, then advance.
  function selectChip(opt) {
    const next = applyValue(opt)
    if (!next) return
    if (prefersReduced()) { advance(next); return }
    setSelecting((opt || '').trim())
    timer.current = setTimeout(() => { setSelecting(null); advance(next) }, 240)
  }
  // Autocomplete match or typed value: advance immediately.
  function selectValue(v) {
    const next = applyValue(v)
    if (next) advance(next)
  }
  function skip() { advance(selections) }
  function prev() { if (current > 0) setCurrent((c) => c - 1) }

  function submitCustom(e) {
    e.preventDefault()
    selectValue(custom)
  }
  function onInputKey(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (matches.length) setActiveMatch((a) => Math.min(a + 1, matches.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveMatch((a) => Math.max(a - 1, -1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (activeMatch >= 0 && matches[activeMatch]) selectValue(matches[activeMatch])
      else selectValue(custom)
    } else if (e.key === 'Escape') {
      if (custom) { e.stopPropagation(); setCustom(''); setActiveMatch(-1) }
      // else: let it bubble to the card and dismiss
    }
  }
  function onCardKey(e) {
    if (e.key === 'Escape') { e.preventDefault(); onDismiss() }
  }

  const chosen = steps.map((s) => selections[s.key]).filter(Boolean)

  return (
    <div className="sc-card" role="group" aria-label="Refine your query suggestions" onKeyDown={onCardKey}>
      <div className="sc-header">
        <span className="sc-title" aria-live="polite">{step.title}</span>
        <div className="sc-nav">
          <span className="sc-dots" aria-hidden="true">
            {steps.map((_, i) => (
              <span key={i} className={'sc-dot' + (i === current ? ' active' : i < current ? ' done' : '')} />
            ))}
          </span>
          <span className="sc-hint">{current + 1} / {steps.length}</span>
          <button className="sc-iconbtn" onClick={prev} disabled={current === 0} aria-label="Previous step">
            <ChevronLeft size={16} />
          </button>
          <button className="sc-iconbtn" onClick={skip} aria-label="Next step">
            <ChevronRight size={16} />
          </button>
          <button className="sc-iconbtn" onClick={onDismiss} aria-label="Close suggestions">
            <X size={16} />
          </button>
        </div>
      </div>

      {chosen.length > 0 && (
        <div className="sc-chips">
          {chosen.map((v) => (
            <span className="sc-chip" key={v}><Check size={12} />{v}</span>
          ))}
        </div>
      )}

      {step.chips && (
        <div className="sc-options" role="radiogroup" aria-label={step.title} key={current}>
          {step.options.map((opt, i) => (
            <button
              key={opt}
              ref={i === 0 ? firstOptRef : undefined}
              type="button"
              className={'sc-opt' + (selecting === opt ? ' selecting' : '')}
              style={{ '--i': i }}
              role="radio"
              aria-checked={selections[step.key] === opt}
              onClick={() => selectChip(opt)}
            >
              {opt}
            </button>
          ))}
        </div>
      )}

      <div className="sc-input-wrap">
        <form className="sc-input-row" onSubmit={submitCustom}>
          <input
            ref={inputRef}
            className="sc-input"
            type="text"
            value={custom}
            onChange={(e) => { setCustom(e.target.value); setActiveMatch(-1) }}
            onKeyDown={onInputKey}
            placeholder={step.placeholder}
            aria-label={step.placeholder}
            autoComplete="off"
            role="combobox"
            aria-expanded={matches.length > 0}
            aria-controls="sc-ac-list"
          />
          <button className="sc-input-go" type="submit" disabled={!custom.trim()} aria-label="Use your input">
            <ArrowRight size={16} />
          </button>
        </form>
        {matches.length > 0 && (
          <ul className="sc-ac" id="sc-ac-list" role="listbox">
            {matches.map((m, i) => (
              <li
                key={m}
                role="option"
                aria-selected={i === activeMatch}
                className={'sc-ac-item' + (i === activeMatch ? ' active' : '')}
                onMouseDown={(e) => { e.preventDefault(); selectValue(m) }}
                onMouseEnter={() => setActiveMatch(i)}
              >
                {m}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="sc-footer">
        <button className="sc-skip" onClick={skip}>{isLast ? 'Finish' : 'Skip'}</button>
      </div>
    </div>
  )
}
