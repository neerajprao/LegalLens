import { useState } from 'react'
import { api, type AuditLogResult } from '../api'
import { PanelHeader } from './PanelHeader'
import { buttonStyle, colors, disabledStyle, emptyStateStyle, panelStyle, tagStyle } from './shared'

export function AuditLogPanel({ caseId }: { caseId: string }) {
  const [result, setResult] = useState<AuditLogResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      setResult(await api.auditLog(caseId))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={panelStyle}>
      <PanelHeader icon="🕵️" title="Audit Log" subtitle="Every material change to this case, in order — the record of what the system knew and when." />
      <button style={{ ...buttonStyle, marginTop: '0.9rem', ...disabledStyle(loading) }} onClick={load} disabled={loading}>
        {loading ? 'Loading…' : 'View audit log'}
      </button>

      {result && (
        <div style={{ marginTop: '0.75rem' }}>
          {result.entries.map((e) => (
            <div
              key={e.id}
              style={{
                display: 'flex',
                gap: '0.75rem',
                alignItems: 'baseline',
                padding: '0.5rem 0',
                borderBottom: `1px solid ${colors.borderSoft}`,
                fontSize: '0.86rem',
              }}
            >
              <code style={{ fontSize: '0.72rem', flexShrink: 0 }}>{e.created_at}</code>
              <span style={{ ...tagStyle, flexShrink: 0 }}>{e.event_type}</span>
              <span style={{ color: colors.text }}>{e.summary}</span>
            </div>
          ))}
          {result.entries.length === 0 && <p style={emptyStateStyle}>No entries yet.</p>}
        </div>
      )}
    </section>
  )
}
