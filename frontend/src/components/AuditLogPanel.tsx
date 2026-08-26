import { useState } from 'react'
import { api, type AuditLogResult } from '../api'
import { buttonStyle, panelStyle } from './shared'

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
      <h2>Audit Log</h2>
      <p style={{ fontSize: '0.85em', color: '#666' }}>
        Every material change to this case, in order — the record of what the system knew and when.
      </p>
      <button style={buttonStyle} onClick={load} disabled={loading}>
        {loading ? 'Loading…' : 'View audit log'}
      </button>

      {result && (
        <ul style={{ marginTop: '0.75rem' }}>
          {result.entries.map((e) => (
            <li key={e.id}>
              <code style={{ fontSize: '0.8em', color: '#888' }}>{e.created_at}</code> [{e.event_type}] {e.summary}
            </li>
          ))}
          {result.entries.length === 0 && <li>No entries yet.</li>}
        </ul>
      )}
    </section>
  )
}
