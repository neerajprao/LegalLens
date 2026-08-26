import { useState } from 'react'
import { api, type CaseStrengthResult } from '../api'
import { buttonStyle, panelStyle, severityColor } from './shared'

const BAND_LABEL: Record<CaseStrengthResult['aggregate_band'], string> = {
  'early-stage': 'Early stage',
  'partially-documented': 'Partially documented',
  'well-documented': 'Well documented',
}

export function CaseStrengthPanel({ caseId }: { caseId: string }) {
  const [result, setResult] = useState<CaseStrengthResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      setResult(await api.caseStrength(caseId))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={panelStyle}>
      <h2>Case Strength</h2>
      <button style={buttonStyle} onClick={load} disabled={loading}>
        {loading ? 'Loading…' : 'View case strength summary'}
      </button>

      {result && (
        <div style={{ marginTop: '0.75rem' }}>
          <div style={{ background: '#e8f0fe', padding: '0.75rem', borderRadius: 6 }}>
            <strong>{BAND_LABEL[result.aggregate_band]}</strong>
            <p style={{ fontSize: '0.85em', color: '#555' }}>{result.aggregate_band_disclaimer}</p>
          </div>

          <h3>Evidence coverage</h3>
          <ul>
            {result.evidence_coverage.map((c) => (
              <li key={c.claim_id}>
                <strong>[{c.evidence_status}]</strong> {c.description}
              </li>
            ))}
            {result.evidence_coverage.length === 0 && <li>No claims recorded yet.</li>}
          </ul>

          <h3>Disputed facts</h3>
          <ul>
            {result.disputed_facts.map((d) => (
              <li key={d.turn_id}>
                "{d.answer}" — {d.explanation}
              </li>
            ))}
            {result.disputed_facts.length === 0 && <li>None flagged.</li>}
          </ul>

          <h3>Legal uncertainty</h3>
          <ul>
            {result.legal_uncertainty.map((u, i) => (
              <li key={i}>
                {u.description}
                {u.hypotheses.length > 0 && <> ({u.hypotheses.join(', ')})</>}
              </li>
            ))}
            {result.legal_uncertainty.length === 0 && <li>None flagged.</li>}
          </ul>

          <h3>Counterarguments</h3>
          <ul>
            {result.counterarguments.map((w, i) => (
              <li key={i} style={{ color: severityColor[w.severity ?? 'unspecified'] }}>
                [{w.severity ?? 'unspecified'}] {w.description}
              </li>
            ))}
            {result.counterarguments.length === 0 && <li>None flagged.</li>}
          </ul>

          {result.flagged_conflicts.length > 0 && (
            <>
              <h3>Unresolved tension between agents</h3>
              {result.flagged_conflicts.map((c, i) => (
                <p key={i} style={{ background: '#fdecea', padding: '0.5rem', borderRadius: 4 }}>
                  {c.description}
                </p>
              ))}
            </>
          )}
        </div>
      )}
    </section>
  )
}
