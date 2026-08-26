import { useState } from 'react'
import { api, type TimelineResult } from '../api'
import { buttonStyle, panelStyle } from './shared'

export function TimelinePanel({ caseId }: { caseId: string }) {
  const [result, setResult] = useState<TimelineResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      setResult(await api.timeline(caseId))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={panelStyle}>
      <h2>Timeline</h2>
      <button style={buttonStyle} onClick={load} disabled={loading}>
        {loading ? 'Loading…' : 'View timeline'}
      </button>

      {result && (
        <div style={{ marginTop: '0.75rem' }}>
          <ol>
            {result.dated_events.map((e) => (
              <li key={e.id}>
                <strong>{e.occurred_at}</strong> — {e.description}
              </li>
            ))}
            {result.dated_events.length === 0 && <li>No dated events yet.</li>}
          </ol>

          {result.undated_events.length > 0 && (
            <>
              <h3>Undated / unclear-date events</h3>
              <ul>
                {result.undated_events.map((e) => (
                  <li key={e.id}>
                    {e.description} {e.occurred_at && <em>("{e.occurred_at}")</em>}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </section>
  )
}
