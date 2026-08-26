import { useState } from 'react'
import { api, type ClassifyResult } from '../api'
import { buttonStyle, panelStyle } from './shared'

export function ClassificationPanel({ caseId }: { caseId: string }) {
  const [result, setResult] = useState<ClassifyResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function run() {
    setLoading(true)
    try {
      setResult(await api.classify(caseId))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={panelStyle}>
      <h2>Legal Classification &amp; Law Retrieval</h2>
      <button style={buttonStyle} onClick={run} disabled={loading}>
        {loading ? 'Running…' : 'Classify and retrieve provisions'}
      </button>

      {result && (
        <div style={{ marginTop: '0.75rem' }}>
          <h3>Candidate categories (hypotheses, not conclusions)</h3>
          {result.classification.hypotheses.length === 0 && <p>No hypotheses could be formed yet.</p>}
          <ul>
            {result.classification.hypotheses.map((h, i) => (
              <li key={i}>
                <strong>{h.category}</strong> ({h.confidence}) — {h.rationale}
              </li>
            ))}
          </ul>

          <h3>Retrieved provisions</h3>
          {result.retrieval.insufficient_data ? (
            <p style={{ color: '#b7791f' }}>{result.retrieval.note || 'No verified provisions found for these hypotheses.'}</p>
          ) : (
            Object.entries(result.retrieval.retrieved).map(([category, hits]) => (
              <div key={category}>
                <p style={{ fontWeight: 600 }}>{category}</p>
                <ul>
                  {hits.map((hit, i) => (
                    <li key={i}>
                      {String(hit.metadata.act_name)} §{String(hit.metadata.section_number)} —{' '}
                      {hit.text.slice(0, 150)}...
                    </li>
                  ))}
                </ul>
              </div>
            ))
          )}
        </div>
      )}
    </section>
  )
}
