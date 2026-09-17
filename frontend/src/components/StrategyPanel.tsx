import { useEffect, useRef, useState } from 'react'
import { api, type StrategyResult } from '../api'
import { PanelHeader } from './PanelHeader'
import { buttonStyle, calloutStyle, cardStyle, colors, disabledStyle, emptyStateStyle, panelStyle } from './shared'

export function StrategyPanel({ caseId, triggerSignal = 0 }: { caseId: string; triggerSignal?: number }) {
  const [result, setResult] = useState<StrategyResult | null>(null)
  const [loading, setLoading] = useState(false)
  // Once the user has acknowledged the non-advice disclaimer once, a re-run from "Analyze the
  // case" (or from clicking this panel's own button again) should go straight to real options
  // rather than re-showing the gate — the acknowledgment was of the disclaimer itself (CLAUDE.md
  // §8.5), not of one specific run, so it shouldn't need repeating every time within a session.
  const acknowledgedRef = useRef(false)

  async function fetchGated() {
    setLoading(true)
    try {
      setResult(await api.strategy(caseId, acknowledgedRef.current))
    } finally {
      setLoading(false)
    }
  }

  async function acknowledgeAndFetch() {
    acknowledgedRef.current = true
    setLoading(true)
    try {
      setResult(await api.strategy(caseId, true))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (triggerSignal > 0) fetchGated()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggerSignal])

  return (
    <section style={panelStyle}>
      <PanelHeader icon="🧭" title="Legal Strategy" subtitle="Non-binding, ranked options based on currently known facts — never a directive." />

      {!result && (
        <button style={{ ...buttonStyle, marginTop: '0.9rem', ...disabledStyle(loading) }} onClick={fetchGated} disabled={loading}>
          {loading ? 'Loading…' : 'View suggested options'}
        </button>
      )}

      {result?.gated && (
        <div style={{ marginTop: '0.9rem' }}>
          <div style={calloutStyle.warn}>{result.disclaimer}</div>
          <button style={{ ...buttonStyle, marginTop: '0.75rem', ...disabledStyle(loading) }} onClick={acknowledgeAndFetch} disabled={loading}>
            {loading ? 'Loading…' : 'I understand — show suggested options'}
          </button>
        </div>
      )}

      {result && !result.gated && (
        <div style={{ marginTop: '0.5rem' }}>
          {result.insufficient_case_state && <p style={emptyStateStyle}>Not enough case information yet.</p>}

          {result.suggested_best_path && (
            <div style={calloutStyle.info}>
              <strong style={{ color: colors.goldBright }}>Currently strongest option:</strong>{' '}
              {result.suggested_best_path.description}
              <p style={{ fontSize: '0.85rem', marginTop: '0.35rem' }}>{result.suggested_best_path.rationale}</p>
            </div>
          )}

          <h3>All options</h3>
          {(result.options ?? []).map((opt, i) => (
            <div key={i} style={cardStyle}>
              <strong style={{ color: colors.text, fontSize: '0.92rem' }}>{opt.description}</strong>
              <p style={{ fontSize: '0.87rem', marginTop: '0.3rem' }}>{opt.rationale}</p>
              {opt.citations.length > 0 && (
                <p style={{ fontSize: '0.78rem', color: colors.textFaint, marginTop: '0.3rem' }}>{opt.citations.join(' · ')}</p>
              )}
            </div>
          ))}
          {(result.options ?? []).length === 0 && <p style={emptyStateStyle}>No options generated.</p>}
        </div>
      )}
    </section>
  )
}
