import { useState } from 'react'
import { api, type TimelineResult } from '../api'
import { PanelHeader } from './PanelHeader'
import { buttonStyle, colors, disabledStyle, emptyStateStyle, panelStyle } from './shared'

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
      <PanelHeader icon="🕐" title="Timeline" subtitle="Events sorted chronologically, with unclear dates kept visibly separate rather than guessed." />
      <button style={{ ...buttonStyle, marginTop: '0.9rem', ...disabledStyle(loading) }} onClick={load} disabled={loading}>
        {loading ? 'Loading…' : 'View timeline'}
      </button>

      {result && (
        <div style={{ marginTop: '0.75rem' }}>
          {result.dated_events.length === 0 ? (
            <p style={emptyStateStyle}>No dated events yet.</p>
          ) : (
            <div style={{ position: 'relative', paddingLeft: '1.1rem' }}>
              <div style={{ position: 'absolute', left: 4, top: 6, bottom: 6, width: 1, background: colors.border }} />
              {result.dated_events.map((e) => (
                <div key={e.id} style={{ position: 'relative', marginBottom: '0.85rem' }}>
                  <span
                    style={{
                      position: 'absolute',
                      left: '-1.1rem',
                      top: 4,
                      width: 9,
                      height: 9,
                      borderRadius: '50%',
                      background: colors.gold,
                      boxShadow: `0 0 0 3px ${colors.goldSoft}`,
                    }}
                  />
                  <code style={{ fontSize: '0.78rem' }}>{e.occurred_at}</code>
                  <p style={{ marginTop: '0.2rem', color: colors.text, fontSize: '0.9rem' }}>{e.description}</p>
                </div>
              ))}
            </div>
          )}

          {result.undated_events.length > 0 && (
            <>
              <h3>Undated / unclear-date events</h3>
              <ul>
                {result.undated_events.map((e) => (
                  <li key={e.id}>
                    {e.description} {e.occurred_at && <em style={{ color: colors.textFaint }}>("{e.occurred_at}")</em>}
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
