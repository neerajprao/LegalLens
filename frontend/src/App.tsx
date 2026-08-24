import { useState } from 'react'
import './App.css'

const API_BASE = 'http://localhost:8000'

type FactExtractionResult = {
  entities?: unknown[]
  events?: { description: string; occurred_at: string; is_approximate_date: boolean }[]
  statements?: { raw_text: string; classification: string }[]
  parse_error?: string
}

function App() {
  const [caseId, setCaseId] = useState<string | null>(null)
  const [narrative, setNarrative] = useState('')
  const [result, setResult] = useState<FactExtractionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function startCase() {
    setError(null)
    const res = await fetch(`${API_BASE}/cases`, { method: 'POST' })
    if (!res.ok) {
      setError('Could not start a case. Is the backend running on :8000?')
      return
    }
    const data = await res.json()
    setCaseId(data.id)
  }

  async function submitNarrative() {
    if (!caseId || !narrative.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/cases/${caseId}/narrative`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ narrative }),
      })
      if (!res.ok) throw new Error(`Request failed: ${res.status}`)
      const data = await res.json()
      setResult(data.fact_extraction)
    } catch {
      setError('Fact extraction failed. Check the backend logs and ANTHROPIC_API_KEY.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: '2rem auto', padding: '0 1rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1>Legal Lens</h1>
      <p style={{ background: '#fff3cd', padding: '0.75rem', borderRadius: 6 }}>
        This is an early development build. Nothing here is legal advice — all output is an
        AI-generated draft that requires professional review before any reliance on it.
      </p>

      {!caseId ? (
        <button onClick={startCase}>Start a case</button>
      ) : (
        <p>Case started: <code>{caseId}</code></p>
      )}

      {caseId && (
        <>
          <textarea
            value={narrative}
            onChange={(e) => setNarrative(e.target.value)}
            placeholder="Describe your situation in your own words..."
            rows={8}
            style={{ width: '100%', marginTop: '1rem' }}
          />
          <div style={{ marginTop: '0.5rem' }}>
            <button onClick={submitNarrative} disabled={loading || !narrative.trim()}>
              {loading ? 'Extracting facts…' : 'Submit'}
            </button>
          </div>
        </>
      )}

      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {result && (
        <section style={{ marginTop: '1.5rem' }}>
          <h2>Extracted statements</h2>
          <ul>
            {(result.statements ?? []).map((s, i) => (
              <li key={i}>
                <strong>[{s.classification}]</strong> {s.raw_text}
              </li>
            ))}
          </ul>
          <h2>Extracted events</h2>
          <ul>
            {(result.events ?? []).map((e, i) => (
              <li key={i}>
                {e.description} {e.occurred_at && `(${e.occurred_at}${e.is_approximate_date ? ', approximate' : ''})`}
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  )
}

export default App
