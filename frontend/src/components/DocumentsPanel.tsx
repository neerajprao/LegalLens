import { useState } from 'react'
import { api, type DocumentResult, type DraftType } from '../api'
import { buttonStyle, panelStyle } from './shared'

const DRAFT_TYPES: { value: DraftType; label: string }[] = [
  { value: 'complaint', label: 'Complaint' },
  { value: 'legal_notice', label: 'Legal notice' },
  { value: 'case_summary', label: 'Case summary' },
  { value: 'chronology', label: 'Chronology' },
  { value: 'evidence_list', label: 'Evidence list' },
  { value: 'statement', label: 'Statement' },
  { value: 'question_set', label: 'Question set' },
]

export function DocumentsPanel({ caseId }: { caseId: string }) {
  const [draftType, setDraftType] = useState<DraftType>('case_summary')
  const [result, setResult] = useState<DocumentResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function generate() {
    setLoading(true)
    try {
      setResult(await api.generateDocument(caseId, draftType))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={panelStyle}>
      <h2>Document Drafts</h2>
      <p style={{ background: '#fff3cd', padding: '0.5rem', borderRadius: 4, fontSize: '0.9em' }}>
        Generated drafts are AI-assisted and require professional review before any use.
      </p>
      <select value={draftType} onChange={(e) => setDraftType(e.target.value as DraftType)}>
        {DRAFT_TYPES.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>
      <button style={{ ...buttonStyle, marginLeft: '0.5rem' }} onClick={generate} disabled={loading}>
        {loading ? 'Generating…' : 'Generate draft'}
      </button>

      {result && (
        <div style={{ marginTop: '0.75rem' }}>
          {result.insufficient_case_state && <p>Not enough case information yet to draft this document.</p>}
          {result.citation_warning && (
            <p style={{ background: '#fed7d7', padding: '0.5rem', borderRadius: 4, fontSize: '0.9em' }}>
              {result.citation_warning}
              {result.unverified_citations_dropped && result.unverified_citations_dropped.length > 0 && (
                <> Unverified: {result.unverified_citations_dropped.join(', ')}</>
              )}
            </p>
          )}
          <pre style={{ whiteSpace: 'pre-wrap', background: '#f7f7f7', padding: '0.75rem', borderRadius: 6 }}>
            {result.content}
          </pre>
          {result.verified_citations && result.verified_citations.length > 0 && (
            <p style={{ fontSize: '0.8em', color: '#666' }}>
              Verified citations: {result.verified_citations.join(', ')}
            </p>
          )}
        </div>
      )}
    </section>
  )
}
