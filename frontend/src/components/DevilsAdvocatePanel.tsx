import { useEffect, useState } from 'react'
import { api, type DevilsAdvocateResult } from '../api'
import { PanelHeader } from './PanelHeader'
import { badgeStyle, buttonStyle, cardStyle, colors, disabledStyle, emptyStateStyle, panelStyle, severityBg, severityColor } from './shared'

export function DevilsAdvocatePanel({ caseId, triggerSignal = 0 }: { caseId: string; triggerSignal?: number }) {
  const [result, setResult] = useState<DevilsAdvocateResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function run() {
    setLoading(true)
    try {
      setResult(await api.devilsAdvocate(caseId))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (triggerSignal > 0) run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggerSignal])

  return (
    <section style={panelStyle}>
      <PanelHeader
        icon="🎭"
        title="Devil's Advocate"
        subtitle="Weaknesses and opposing arguments drawn strictly from your own facts and evidence — nothing invented to attack."
      />
      <button style={{ ...buttonStyle, marginTop: '0.9rem', ...disabledStyle(loading) }} onClick={run} disabled={loading}>
        {loading ? 'Analyzing…' : 'Find weaknesses'}
      </button>

      {result?.insufficient_case_state && <p style={{ ...emptyStateStyle, marginTop: '0.75rem' }}>Not enough case information yet to analyze.</p>}

      {result && !result.insufficient_case_state && (
        <div style={{ marginTop: '0.5rem' }}>
          <h3>Weaknesses</h3>
          {(result.weaknesses ?? []).map((w, i) => {
            const sev = w.severity ?? 'unspecified'
            return (
              <div key={i} style={cardStyle}>
                <span style={badgeStyle(severityColor[sev], severityBg[sev])}>{sev}</span>
                <p style={{ marginTop: '0.35rem', fontSize: '0.9rem', color: colors.text }}>{w.description}</p>
              </div>
            )
          })}
          {(result.weaknesses ?? []).length === 0 && <p style={emptyStateStyle}>None flagged.</p>}

          <h3>Arguments the other side could make</h3>
          <ul>
            {(result.opposing_arguments ?? []).map((a, i) => (
              <li key={i}>{a}</li>
            ))}
            {(result.opposing_arguments ?? []).length === 0 && <li style={emptyStateStyle}>None flagged.</li>}
          </ul>

          <h3>Alternative interpretations</h3>
          <ul>
            {(result.alternative_interpretations ?? []).map((a, i) => (
              <li key={i}>{a}</li>
            ))}
            {(result.alternative_interpretations ?? []).length === 0 && <li style={emptyStateStyle}>None flagged.</li>}
          </ul>
        </div>
      )}
    </section>
  )
}
