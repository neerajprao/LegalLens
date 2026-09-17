import { useEffect, useRef, useState } from 'react'
import { api, type Claim, type EvidenceGap, type EvidenceInventoryItem } from '../api'
import { PanelHeader } from './PanelHeader'
import {
  badgeStyle,
  buttonStyle,
  calloutStyle,
  cardStyle,
  colors,
  dangerGhostButtonStyle,
  disabledStyle,
  dividerStyle,
  emptyStateStyle,
  fieldRowStyle,
  ghostButtonStyle,
  inputStyle,
  panelStyle,
  secondaryButtonStyle,
  statusBg,
  statusColor,
} from './shared'

const CONFIDENCE_LABEL: Record<string, { color: string; bg: string }> = {
  high: { color: colors.ok, bg: colors.okSoft },
  medium: { color: colors.warn, bg: colors.warnSoft },
  low: { color: colors.warn, bg: colors.warnSoft },
  none: { color: colors.danger, bg: colors.dangerSoft },
}

function statusLabel(status: string): string {
  return status.replace(/_/g, ' ')
}

function EvidenceRow({
  item,
  onToggleDispute,
}: {
  item: EvidenceInventoryItem
  onToggleDispute: (item: EvidenceInventoryItem) => void
}) {
  const conf = item.extraction_confidence ? CONFIDENCE_LABEL[item.extraction_confidence] : null
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '0.75rem',
        padding: '0.5rem 0',
        borderBottom: `1px solid ${colors.borderSoft}`,
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={badgeStyle(colors.textDim, 'rgba(255,255,255,0.05)')}>{item.evidence_type}</span>
          {item.has_file && conf && <span style={badgeStyle(conf.color, conf.bg)}>extraction: {item.extraction_confidence}</span>}
          {item.disputed && <span style={badgeStyle(colors.danger, colors.dangerSoft)}>disputed</span>}
        </div>
        <p style={{ marginTop: '0.25rem', fontSize: '0.88rem', color: colors.text }}>
          {item.description || <span style={{ color: colors.textFaint }}>(no description)</span>}
        </p>
      </div>
      <button style={ghostButtonStyle} onClick={() => onToggleDispute(item)}>
        {item.disputed ? 'Clear dispute' : 'Mark disputed'}
      </button>
    </div>
  )
}

function AddEvidenceForm({
  onAdd,
}: {
  onAdd: (type: string, description: string, file: File | null) => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  const [type, setType] = useState('')
  const [description, setDescription] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)

  async function submit() {
    if (!type.trim()) return
    setSaving(true)
    try {
      await onAdd(type, description, file)
      setType('')
      setDescription('')
      setFile(null)
      setOpen(false)
    } finally {
      setSaving(false)
    }
  }

  if (!open) {
    return (
      <button style={{ ...secondaryButtonStyle, marginTop: '0.6rem' }} onClick={() => setOpen(true)}>
        + Add evidence
      </button>
    )
  }

  return (
    <div style={{ ...cardStyle, background: 'transparent', border: `1px dashed ${colors.border}` }}>
      <div style={fieldRowStyle}>
        <input
          value={type}
          onChange={(e) => setType(e.target.value)}
          placeholder="Type (e.g., messages, contract)"
          style={{ ...inputStyle, flex: '1 1 160px' }}
        />
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description"
          style={{ ...inputStyle, flex: '2 1 220px' }}
        />
        <input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.txt"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          style={{ fontSize: '0.8rem', color: colors.textDim, flex: '1 1 160px' }}
        />
      </div>
      <div style={{ marginTop: '0.6rem', display: 'flex', gap: '0.5rem' }}>
        <button style={{ ...buttonStyle, ...disabledStyle(saving || !type.trim()) }} onClick={submit} disabled={saving || !type.trim()}>
          {saving ? 'Adding…' : 'Save evidence'}
        </button>
        <button style={ghostButtonStyle} onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
    </div>
  )
}

export function ClaimsEvidencePanel({
  caseId,
  triggerSignal = 0,
  onCaseChanged,
}: {
  caseId: string
  // Bumped by the "Analyze the case" button in App.tsx so this panel's own "Analyze evidence
  // gaps" step runs alongside every other agent, without touching its individual button.
  triggerSignal?: number
  // Called whenever a claim or evidence item is added/edited/removed/disputed, so the parent
  // can mark "Analyze the case" clickable again — an analysis run before this change no longer
  // reflects the current case.
  onCaseChanged?: () => void
}) {
  const [claims, setClaims] = useState<Claim[]>([])
  const [claimText, setClaimText] = useState('')
  const [addingClaim, setAddingClaim] = useState(false)
  const [inventory, setInventory] = useState<EvidenceInventoryItem[]>([])
  const [gaps, setGaps] = useState<EvidenceGap[] | null>(null)
  const [gapsLoading, setGapsLoading] = useState(false)
  const [uploadNote, setUploadNote] = useState<string | null>(null)
  const [suggesting, setSuggesting] = useState(false)
  const [suggestNote, setSuggestNote] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editText, setEditText] = useState('')
  const claimsRef = useRef(claims)
  claimsRef.current = claims

  async function loadInventory() {
    const result = await api.listEvidence(caseId)
    setInventory(result.evidence)
  }

  // On first mount for a case: load whatever claims already exist (so a reload or a return to
  // this tab doesn't lose them — the panel used to only ever hold claims added in the current
  // session). If there are none yet but the interview has produced facts, auto-fill from them
  // once, rather than leaving the user to retype what they already told the chat.
  useEffect(() => {
    let cancelled = false
    async function load() {
      const result = await api.listClaims(caseId)
      if (cancelled) return
      if (result.claims.length > 0) {
        setClaims(result.claims)
        return
      }
      setSuggesting(true)
      try {
        const suggested = await api.suggestClaims(caseId)
        if (cancelled) return
        if (suggested.claims.length > 0) {
          setClaims(suggested.claims)
          setSuggestNote(`Filled in ${suggested.claims.length} claim${suggested.claims.length === 1 ? '' : 's'} from your interview — edit, remove, or add more below.`)
        }
      } finally {
        if (!cancelled) setSuggesting(false)
      }
    }
    load()
    loadInventory()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId])

  async function addClaim() {
    if (!claimText.trim()) return
    setAddingClaim(true)
    try {
      const claim = await api.createClaim(caseId, claimText)
      setClaims((prev) => [...prev, claim])
      setClaimText('')
      onCaseChanged?.()
    } finally {
      setAddingClaim(false)
    }
  }

  function startEdit(claim: Claim) {
    setEditingId(claim.id)
    setEditText(claim.description)
  }

  async function saveEdit(claimId: string) {
    const text = editText.trim()
    if (!text) return
    const updated = await api.updateClaim(caseId, claimId, text)
    setClaims((prev) => prev.map((c) => (c.id === claimId ? updated : c)))
    setEditingId(null)
    onCaseChanged?.()
  }

  async function removeClaim(claimId: string) {
    await api.deleteClaim(caseId, claimId)
    setClaims((prev) => prev.filter((c) => c.id !== claimId))
    onCaseChanged?.()
  }

  async function addEvidenceFor(linkedClaimId: string | null, type: string, description: string, file: File | null) {
    setUploadNote(null)
    if (file) {
      const result = await api.uploadEvidence(caseId, type, description, linkedClaimId, file)
      setUploadNote(
        result.extraction_confidence === 'none' || result.extraction_confidence === 'low'
          ? `Uploaded — text extraction confidence is "${result.extraction_confidence}"; treat extracted text as unreliable.`
          : `Uploaded — text extracted with "${result.extraction_confidence}" confidence.`,
      )
    } else {
      await api.createEvidence(caseId, type, description, linkedClaimId)
    }
    await loadInventory()
    onCaseChanged?.()
  }

  async function toggleDispute(item: EvidenceInventoryItem) {
    await api.disputeEvidence(caseId, item.id, !item.disputed)
    await loadInventory()
    onCaseChanged?.()
  }

  async function loadGaps() {
    setGapsLoading(true)
    try {
      const result = await api.evidenceGaps(caseId)
      setGaps(result.gaps)
    } finally {
      setGapsLoading(false)
    }
  }

  // Runs alongside every other agent when "Analyze the case" is clicked (see triggerSignal's
  // docstring above) — guarded the same way the button below already is, via a ref rather than a
  // `claims` dependency so this effect only fires on an actual trigger bump, not on every claim
  // list change (which would defeat the point of a single shared "analyze" action).
  useEffect(() => {
    if (triggerSignal > 0 && claimsRef.current.length > 0) loadGaps()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggerSignal])

  const unlinked = inventory.filter((e) => !e.linked_claim_id)

  return (
    <section style={panelStyle}>
      <PanelHeader
        icon="📋"
        title="Claims & Evidence"
        subtitle="Add each claim you're making, then attach supporting evidence directly to it. A claim with no evidence stays visibly unsupported — that distinction is never hidden."
      />

      <div style={{ ...fieldRowStyle, marginTop: '1rem' }}>
        <input
          value={claimText}
          onChange={(e) => setClaimText(e.target.value)}
          placeholder="Describe a claim or allegation…"
          style={{ ...inputStyle, flex: '1 1 320px' }}
          onKeyDown={(e) => e.key === 'Enter' && addClaim()}
        />
        <button
          style={{ ...buttonStyle, ...disabledStyle(addingClaim || !claimText.trim()) }}
          onClick={addClaim}
          disabled={addingClaim || !claimText.trim()}
        >
          + Add claim
        </button>
      </div>

      {suggesting && <p style={{ ...emptyStateStyle, marginTop: '0.9rem' }}>Filling in claims from your interview…</p>}
      {suggestNote && <p style={{ ...calloutStyle.info, marginTop: '0.9rem', padding: '0.5rem 0.7rem', fontSize: '0.82rem' }}>{suggestNote}</p>}
      {!suggesting && claims.length === 0 && <p style={{ ...emptyStateStyle, marginTop: '0.9rem' }}>No claims yet.</p>}

      {claims.map((c) => {
        const evidenceForClaim = inventory.filter((e) => e.linked_claim_id === c.id)
        const isEditing = editingId === c.id
        return (
          <div key={c.id} style={cardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem' }}>
              {isEditing ? (
                <div style={{ ...fieldRowStyle, flex: 1 }}>
                  <input
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    style={{ ...inputStyle, flex: '1 1 240px' }}
                    onKeyDown={(e) => e.key === 'Enter' && saveEdit(c.id)}
                    autoFocus
                  />
                  <button style={ghostButtonStyle} onClick={() => saveEdit(c.id)}>
                    Save
                  </button>
                  <button style={ghostButtonStyle} onClick={() => setEditingId(null)}>
                    Cancel
                  </button>
                </div>
              ) : (
                <p style={{ color: colors.text, fontWeight: 500 }}>{c.description}</p>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
                <span
                  style={badgeStyle(
                    evidenceForClaim.length > 0 ? colors.textDim : colors.danger,
                    evidenceForClaim.length > 0 ? 'rgba(255,255,255,0.05)' : statusBg.unsupported,
                  )}
                >
                  {evidenceForClaim.length > 0
                    ? `${evidenceForClaim.length} evidence item${evidenceForClaim.length === 1 ? '' : 's'}`
                    : 'no evidence yet'}
                </span>
                {!isEditing && (
                  <>
                    <button style={ghostButtonStyle} onClick={() => startEdit(c)}>
                      Edit
                    </button>
                    <button style={dangerGhostButtonStyle} onClick={() => removeClaim(c.id)}>
                      Delete
                    </button>
                  </>
                )}
              </div>
            </div>

            {evidenceForClaim.length > 0 && (
              <div style={{ marginTop: '0.5rem' }}>
                {evidenceForClaim.map((item) => (
                  <EvidenceRow key={item.id} item={item} onToggleDispute={toggleDispute} />
                ))}
              </div>
            )}

            <AddEvidenceForm onAdd={(type, description, file) => addEvidenceFor(c.id, type, description, file)} />
          </div>
        )
      })}

      <hr style={dividerStyle} />
      <h3>General evidence (not linked to a specific claim)</h3>
      {unlinked.length > 0 && (
        <div style={{ marginBottom: '0.5rem' }}>
          {unlinked.map((item) => (
            <EvidenceRow key={item.id} item={item} onToggleDispute={toggleDispute} />
          ))}
        </div>
      )}
      <AddEvidenceForm onAdd={(type, description, file) => addEvidenceFor(null, type, description, file)} />
      {uploadNote && <p style={{ ...emptyStateStyle, marginTop: '0.5rem' }}>{uploadNote}</p>}

      <hr style={dividerStyle} />
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
        <button
          style={{ ...secondaryButtonStyle, ...disabledStyle(gapsLoading || claims.length === 0) }}
          onClick={loadGaps}
          disabled={gapsLoading || claims.length === 0}
        >
          {gapsLoading ? 'Analyzing…' : 'Analyze evidence gaps'}
        </button>
      </div>

      {gaps && (
        <div style={{ marginTop: '0.75rem' }}>
          {gaps.map((g) => (
            <div key={g.claim_id} style={cardStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem' }}>
                <p style={{ color: colors.text }}>{g.claim_description}</p>
                <span style={badgeStyle(statusColor[g.evidence_status] ?? colors.textFaint, statusBg[g.evidence_status] ?? 'rgba(255,255,255,0.05)')}>
                  {statusLabel(g.evidence_status)}
                </span>
              </div>
              {g.suggested_evidence_types.length > 0 && (
                <p style={{ ...emptyStateStyle, marginTop: '0.35rem' }}>
                  Consider adding: {g.suggested_evidence_types.join(', ')}
                </p>
              )}
              {g.low_confidence_evidence_ids.length > 0 && (
                <p style={{ ...calloutStyle.warn, marginTop: '0.5rem', padding: '0.5rem 0.7rem', fontSize: '0.8rem' }}>
                  Some linked evidence has low-confidence extracted text.
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
