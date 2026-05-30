import { useState, useRef, useEffect, useMemo } from 'react'
import { ChevronLeft, ChevronRight, ArrowRight, X, Check } from 'lucide-react'
import './SuggestionCard.css'

// Each missing query dimension becomes one step (only those with suggestions).
const STEP_DEFS = [
  { key: 'country', src: 'countries', title: 'Hangi ülke hakkında bilgi almak istiyorsunuz?', placeholder: 'veya bir ülke yazın…' },
  { key: 'date', src: 'time_periods', title: 'Hangi zaman aralığı?', placeholder: 'veya zaman aralığı yazın…' },
  { key: 'theme', src: 'themes', title: 'Hangi konu?', placeholder: 'veya bir konu yazın…' },
]

/**
 * Multi-step suggestion card (React island).
 * Options are shown as side-by-side wrapping chips; the user can also type a
 * custom answer for the current step. Props:
 *   clarification: { suggestions: { countries, time_periods, themes } }
 *   onApply: (values: string[]) => void   // chosen values in step order
 *   onDismiss: () => void
 */
export default function SuggestionCard({ clarification, onApply, onDismiss }) {
  const steps = useMemo(() => {
    const s = clarification?.suggestions || {}
    return STEP_DEFS
      .filter((d) => Array.isArray(s[d.src]) && s[d.src].length)
      .map((d) => ({ key: d.key, title: d.title, placeholder: d.placeholder, options: s[d.src] }))
  }, [clarification])

  const [current, setCurrent] = useState(0)
  const [selections, setSelections] = useState({})
  const [custom, setCustom] = useState('')
  const firstOptRef = useRef(null)

  // On each step, clear the typed value and move focus to the first chip.
  useEffect(() => {
    setCustom('')
    firstOptRef.current?.focus({ preventScroll: true })
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
    const v = (opt || '').trim()
    if (!v) return
    const next = { ...selections, [step.key]: v }
    setSelections(next)
    advance(next)
  }
  function skip() { advance(selections) }
  function prev() { if (current > 0) setCurrent((c) => c - 1) }

  function submitCustom(e) {
    e.preventDefault()
    select(custom)
  }
  function onKeyDown(e) {
    // Keep it simple and conflict-free with the text input: Esc dismisses;
    // chips are native buttons (Enter/Space/click) and the input owns its keys.
    if (e.key === 'Escape') { e.preventDefault(); onDismiss() }
  }

  const chosen = steps.map((s) => selections[s.key]).filter(Boolean)

  return (
    <div
      className="sc-card"
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

      <div className="sc-options" role="radiogroup" aria-label={step.title} key={current}>
        {step.options.map((opt, i) => (
          <button
            key={opt}
            ref={i === 0 ? firstOptRef : undefined}
            type="button"
            className="sc-opt"
            style={{ '--i': i }}
            role="radio"
            aria-checked={selections[step.key] === opt}
            onClick={() => select(opt)}
          >
            {opt}
          </button>
        ))}
      </div>

      <form className="sc-input-row" onSubmit={submitCustom}>
        <input
          className="sc-input"
          type="text"
          value={custom}
          onChange={(e) => setCustom(e.target.value)}
          placeholder={step.placeholder}
          aria-label={step.placeholder}
        />
        <button className="sc-input-go" type="submit" disabled={!custom.trim()} aria-label="Yazdığını kullan">
          <ArrowRight size={16} />
        </button>
      </form>

      <div className="sc-footer">
        <button className="sc-skip" onClick={skip}>{isLast ? 'Bitir' : 'Atla'}</button>
      </div>
    </div>
  )
}
