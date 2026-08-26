import { useState } from 'react'
import { api, type DevilsAdvocateResult } from '../api'
import { buttonStyle, panelStyle, severityColor } from './shared'

export function DevilsAdvocatePanel({ caseId }: { caseId: string }) {
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

  return (
    <section style={panelStyle}>
      <h2>Devil's Advocate</h2>
      <button style={buttonStyle} onClick={run} disabled={loading}>
        {loading ? 'Analyzing…' : 'Find weaknesses'}
      </button>

      {result?.insufficient_case_state && <p>Not enough case information yet to analyze.</p>}

      {result && !result.insufficient_case_state && (
        <div style={{ marginTop: '0.75rem' }}>
          <h3>Weaknesses</h3>
          <ul>
            {result.weaknesses.map((w, i) => (
              <li key={i} style={{ color: severityColor[w.severity ?? 'unspecified'] }}>
                [{w.severity ?? 'unspecified'}] {w.description}
              </li>
            ))}
          </ul>

          <h3>Arguments the other side could make</h3>
          <ul>
            {result.opposing_arguments.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>

          <h3>Alternative interpretations</h3>
          <ul>
            {result.alternative_interpretations.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
