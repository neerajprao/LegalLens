import { useState } from 'react'
import { api, type DocumentResult, type DraftType } from '../api'
import { PanelHeader } from './PanelHeader'
import { buttonStyle, calloutStyle, colors, disabledStyle, emptyStateStyle, panelStyle, selectStyle } from './shared'

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
      <PanelHeader icon="📄" title="Document Drafts" subtitle="AI-assisted drafts that require professional review before any use." />

      <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.9rem', flexWrap: 'wrap' }}>
        <select value={draftType} onChange={(e) => setDraftType(e.target.value as DraftType)} style={selectStyle}>
          {DRAFT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <button style={{ ...buttonStyle, ...disabledStyle(loading) }} onClick={generate} disabled={loading}>
          {loading ? 'Generating…' : 'Generate draft'}
        </button>
      </div>

      {result && (
        <div style={{ marginTop: '1rem' }}>
          {result.insufficient_case_state && <p style={emptyStateStyle}>Not enough case information yet to draft this document.</p>}
          {result.citation_warning && (
            <div style={{ ...calloutStyle.danger, marginBottom: '0.75rem' }}>
              {result.citation_warning}
              {result.unverified_citations_dropped && result.unverified_citations_dropped.length > 0 && (
                <> Unverified: {result.unverified_citations_dropped.join(', ')}</>
              )}
            </div>
          )}
          <pre
            style={{
              whiteSpace: 'pre-wrap',
              background: colors.bg,
              border: `1px solid ${colors.border}`,
              padding: '1rem',
              borderRadius: 10,
              fontSize: '0.86rem',
              lineHeight: 1.6,
              color: colors.text,
            }}
          >
            {result.content}
          </pre>
          {result.verified_citations && result.verified_citations.length > 0 && (
            <p style={{ ...emptyStateStyle, marginTop: '0.5rem' }}>
              Verified citations: {result.verified_citations.join(', ')}
            </p>
          )}
        </div>
      )}
    </section>
  )
}
