import { useState, useRef, useEffect, useMemo } from 'react'
import { ChevronLeft, ChevronRight, ArrowRight, X, Check } from 'lucide-react'
import './SuggestionCard.css'

// Each missing query dimension becomes one step (only those with suggestions).
const STEP_DEFS = [
  { key: 'country', src: 'countries', title: 'Hangi ülke hakkında bilgi almak istiyorsunuz?' },
  { key: 'date', src: 'time_periods', title: 'Hangi zaman aralığı?' },
  { key: 'theme', src: 'themes', title: 'Hangi konu?' },
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
      .map((d) => ({ key: d.key, title: d.title, options: s[d.src] }))
  }, [clarification])

  const [current, setCurrent] = useState(0)
  const [selections, setSelections] = useState({})
  const [focused, setFocused] = useState(0)
  const cardRef = useRef(null)

  // Move keyboard focus to the card on mount and whenever the step changes.
  useEffect(() => {
    setFocused(0)
    cardRef.current?.focus()
  }, [current])

  if (!steps.length) return null
  const step = steps[current]
  const isLast = current >= steps.length - 1

  function finalize(next) {
    const values = steps.map((s) => next[s.key]).filter(Boolean)
    if (values.length) onApply(values)
    else onDismiss()
  }
  function advance(next) {
    if (current < steps.length - 1) setCurrent((c) => c + 1)
    else finalize(next)
  }
  function select(opt) {
    if (opt == null) return
    const next = { ...selections, [step.key]: opt }
    setSelections(next)
    advance(next)
  }
  function skip() {
    advance(selections)
  }
  function prev() {
    if (current > 0) setCurrent((c) => c - 1)
  }

  function onKeyDown(e) {
    const opts = step.options
    if (e.key === 'Escape') { e.preventDefault(); onDismiss(); return }
    if (e.key === 'ArrowLeft') { e.preventDefault(); prev(); return }
    if (e.key === 'ArrowRight') { e.preventDefault(); skip(); return }
    if (e.key === 'ArrowDown') { e.preventDefault(); setFocused((f) => Math.min(f + 1, opts.length - 1)); return }
    if (e.key === 'ArrowUp') { e.preventDefault(); setFocused((f) => Math.max(f - 1, 0)); return }
    if (e.key === 'Enter') { e.preventDefault(); select(opts[focused]); return }
    if (/^[1-9]$/.test(e.key)) {
      const idx = parseInt(e.key, 10) - 1
      if (idx < opts.length) { e.preventDefault(); select(opts[idx]) }
    }
  }

  const chosen = steps.map((s) => selections[s.key]).filter(Boolean)

  return (
    <div
      className="sc-card"
      ref={cardRef}
      tabIndex={0}
      role="group"
      aria-label="Sorgunuzu detaylandırma önerileri"
      onKeyDown={onKeyDown}
    >
      <div className="sc-header">
        <span className="sc-title" aria-live="polite">{step.title}</span>
        <div className="sc-nav">
          <span className="sc-dots" aria-hidden="true">
            {steps.map((_, i) => (
              <span key={i} className={'sc-dot' + (i === current ? ' active' : i < current ? ' done' : '')} />
            ))}
          </span>
          <span className="sc-hint">{current + 1} / {steps.length}</span>
          <button className="sc-iconbtn" onClick={prev} disabled={current === 0} aria-label="Önceki adım">
            <ChevronLeft size={16} />
          </button>
          <button className="sc-iconbtn" onClick={skip} aria-label="Sonraki adım">
            <ChevronRight size={16} />
          </button>
          <button className="sc-iconbtn" onClick={onDismiss} aria-label="Önerileri kapat">
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

      <ul className="sc-options" role="radiogroup" aria-label={step.title} key={current}>
        {step.options.map((opt, i) => (
          <li key={opt}>
            <button
              type="button"
              className={'sc-option' + (i === focused ? ' focused' : '')}
              style={{ '--i': i }}
              role="radio"
              aria-checked={selections[step.key] === opt}
              tabIndex={-1}
              onClick={() => select(opt)}
              onMouseEnter={() => setFocused(i)}
            >
              <span className="sc-num" aria-hidden="true">{i + 1}</span>
              <span className="sc-label">{opt}</span>
              <ArrowRight className="sc-arrow" size={16} />
            </button>
          </li>
        ))}
      </ul>

      <div className="sc-footer">
        <button className="sc-skip" onClick={skip}>{isLast ? 'Bitir' : 'Atla'}</button>
        <button className="sc-reply" onClick={onDismiss}>veya doğrudan yazın</button>
      </div>
    </div>
  )
}
