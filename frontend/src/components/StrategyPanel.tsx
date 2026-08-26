import { useState } from 'react'
import { api, type StrategyResult } from '../api'
import { buttonStyle, panelStyle } from './shared'

export function StrategyPanel({ caseId }: { caseId: string }) {
  const [result, setResult] = useState<StrategyResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function fetchGated() {
    setLoading(true)
    try {
      setResult(await api.strategy(caseId, false))
    } finally {
      setLoading(false)
    }
  }

  async function acknowledgeAndFetch() {
    setLoading(true)
    try {
      setResult(await api.strategy(caseId, true))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={panelStyle}>
      <h2>Legal Strategy</h2>

      {!result && (
        <button style={buttonStyle} onClick={fetchGated} disabled={loading}>
          {loading ? 'Loading…' : 'View suggested options'}
        </button>
      )}

      {result?.gated && (
        <div>
          <p style={{ background: '#fff3cd', padding: '0.75rem', borderRadius: 6 }}>{result.disclaimer}</p>
          <button style={buttonStyle} onClick={acknowledgeAndFetch} disabled={loading}>
            {loading ? 'Loading…' : 'I understand — show suggested options'}
          </button>
        </div>
      )}

      {result && !result.gated && (
        <div style={{ marginTop: '0.75rem' }}>
          {result.insufficient_case_state && <p>Not enough case information yet.</p>}

          {result.suggested_best_path && (
            <div style={{ background: '#e8f0fe', padding: '0.75rem', borderRadius: 6 }}>
              <strong>Currently strongest option:</strong> {result.suggested_best_path.description}
              <p style={{ fontSize: '0.9em', color: '#555' }}>{result.suggested_best_path.rationale}</p>
            </div>
          )}

          <h3>All options</h3>
          <ul>
            {(result.options ?? []).map((opt, i) => (
              <li key={i}>
                <strong>{opt.description}</strong> — {opt.rationale}
                {opt.citations.length > 0 && <> ({opt.citations.join('; ')})</>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
