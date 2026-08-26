import { useState } from 'react'
import { api, type Claim, type EvidenceGap } from '../api'
import { buttonStyle, panelStyle } from './shared'

export function ClaimsEvidencePanel({ caseId }: { caseId: string }) {
  const [claims, setClaims] = useState<Claim[]>([])
  const [claimText, setClaimText] = useState('')
  const [evidenceType, setEvidenceType] = useState('')
  const [evidenceDescription, setEvidenceDescription] = useState('')
  const [linkedClaimId, setLinkedClaimId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [gaps, setGaps] = useState<EvidenceGap[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [uploadNote, setUploadNote] = useState<string | null>(null)

  async function addClaim() {
    if (!claimText.trim()) return
    const claim = await api.createClaim(caseId, claimText)
    setClaims((prev) => [...prev, claim])
    setClaimText('')
  }

  async function addEvidence() {
    if (!evidenceType.trim()) return
    setUploadNote(null)
    if (file) {
      const result = await api.uploadEvidence(caseId, evidenceType, evidenceDescription, linkedClaimId || null, file)
      setUploadNote(
        result.extraction_confidence === 'none' || result.extraction_confidence === 'low'
          ? `Uploaded, but text extraction confidence is "${result.extraction_confidence}" — treat extracted text as unreliable.`
          : `Uploaded, text extracted with "${result.extraction_confidence}" confidence.`,
      )
    } else {
      await api.createEvidence(caseId, evidenceType, evidenceDescription, linkedClaimId || null)
    }
    setEvidenceType('')
    setEvidenceDescription('')
    setLinkedClaimId('')
    setFile(null)
  }

  async function loadGaps() {
    setLoading(true)
    try {
      const result = await api.evidenceGaps(caseId)
      setGaps(result.gaps)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={panelStyle}>
      <h2>Claims &amp; Evidence</h2>

      <div>
        <input
          value={claimText}
          onChange={(e) => setClaimText(e.target.value)}
          placeholder="Describe a claim/allegation..."
          style={{ width: '60%' }}
        />
        <button style={{ ...buttonStyle, marginLeft: '0.5rem' }} onClick={addClaim} disabled={!claimText.trim()}>
          Add claim
        </button>
      </div>

      {claims.length > 0 && (
        <ul>
          {claims.map((c) => (
            <li key={c.id}>
              {c.description} — <em>{c.status}</em>
            </li>
          ))}
        </ul>
      )}

      <div style={{ marginTop: '0.75rem' }}>
        <input
          value={evidenceType}
          onChange={(e) => setEvidenceType(e.target.value)}
          placeholder="Evidence type (e.g., messages, document)"
        />
        <input
          value={evidenceDescription}
          onChange={(e) => setEvidenceDescription(e.target.value)}
          placeholder="Description"
          style={{ marginLeft: '0.5rem' }}
        />
        <select value={linkedClaimId} onChange={(e) => setLinkedClaimId(e.target.value)} style={{ marginLeft: '0.5rem' }}>
          <option value="">Link to claim (optional)</option>
          {claims.map((c) => (
            <option key={c.id} value={c.id}>
              {c.description.slice(0, 40)}
            </option>
          ))}
        </select>
        <input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.txt"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          style={{ marginLeft: '0.5rem' }}
        />
        <button style={{ ...buttonStyle, marginLeft: '0.5rem' }} onClick={addEvidence} disabled={!evidenceType.trim()}>
          Add evidence
        </button>
      </div>
      {uploadNote && <p style={{ fontSize: '0.85em', color: '#666' }}>{uploadNote}</p>}

      <div style={{ marginTop: '0.75rem' }}>
        <button style={buttonStyle} onClick={loadGaps} disabled={loading || claims.length === 0}>
          {loading ? 'Analyzing…' : 'Analyze evidence gaps'}
        </button>
      </div>

      {gaps && (
        <ul style={{ marginTop: '0.5rem' }}>
          {gaps.map((g) => (
            <li key={g.claim_id}>
              <strong>[{g.evidence_status}]</strong> {g.claim_description}
              {g.suggested_evidence_types.length > 0 && (
                <> — consider: {g.suggested_evidence_types.join(', ')}</>
              )}
              {g.low_confidence_evidence_ids.length > 0 && (
                <span style={{ color: '#b7791f' }}> (some linked evidence has low-confidence extracted text)</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
