import { useState } from 'react'
import { api, type CaseStrengthResult } from '../api'
import { PanelHeader } from './PanelHeader'
import {
  badgeStyle,
  buttonStyle,
  calloutStyle,
  cardStyle,
  colors,
  disabledStyle,
  emptyStateStyle,
  panelStyle,
  severityBg,
  severityColor,
  statusBg,
  statusColor,
} from './shared'

const BAND_LABEL: Record<CaseStrengthResult['aggregate_band'], string> = {
  'early-stage': 'Early stage',
  'partially-documented': 'Partially documented',
  'well-documented': 'Well documented',
}

const BAND_COLOR: Record<CaseStrengthResult['aggregate_band'], string> = {
  'early-stage': colors.danger,
  'partially-documented': colors.warn,
  'well-documented': colors.ok,
}

export function CaseStrengthPanel({ caseId }: { caseId: string }) {
  const [result, setResult] = useState<CaseStrengthResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      setResult(await api.caseStrength(caseId))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={panelStyle}>
      <PanelHeader icon="📊" title="Case Strength" subtitle="A multi-dimensional, non-scored view of documentation completeness — never a probability of success." />
      <button style={{ ...buttonStyle, marginTop: '0.9rem', ...disabledStyle(loading) }} onClick={load} disabled={loading}>
        {loading ? 'Loading…' : 'View case strength summary'}
      </button>

      {result && (
        <div style={{ marginTop: '0.75rem' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '1rem 1.1rem',
              borderRadius: 12,
              border: `1px solid ${BAND_COLOR[result.aggregate_band]}44`,
              background: `${BAND_COLOR[result.aggregate_band]}14`,
            }}
          >
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: BAND_COLOR[result.aggregate_band],
                flexShrink: 0,
              }}
            />
            <div>
              <strong style={{ color: colors.text, fontSize: '1.02rem' }}>{BAND_LABEL[result.aggregate_band]}</strong>
              <p style={{ fontSize: '0.82rem', marginTop: '0.2rem' }}>{result.aggregate_band_disclaimer}</p>
            </div>
          </div>

          <h3>Evidence coverage</h3>
          {result.evidence_coverage.map((c) => (
            <div key={c.claim_id} style={cardStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem' }}>
                <span style={{ color: colors.text, fontSize: '0.9rem' }}>{c.description}</span>
                <span style={badgeStyle(statusColor[c.evidence_status] ?? colors.textFaint, statusBg[c.evidence_status] ?? 'rgba(255,255,255,0.05)')}>
                  {c.evidence_status.replace(/_/g, ' ')}
                </span>
              </div>
            </div>
          ))}
          {result.evidence_coverage.length === 0 && <p style={emptyStateStyle}>No claims recorded yet.</p>}

          <h3>Disputed facts</h3>
          <ul>
            {result.disputed_facts.map((d) => (
              <li key={d.turn_id}>
                &ldquo;{d.answer}&rdquo;
                {d.contradicts_text && <> contradicts &ldquo;{d.contradicts_text}&rdquo;</>} — {d.explanation}
              </li>
            ))}
            {result.disputed_facts.length === 0 && <li style={emptyStateStyle}>None flagged.</li>}
          </ul>

          <h3>Legal uncertainty</h3>
          <ul>
            {result.legal_uncertainty.map((u, i) => (
              <li key={i}>
                {u.description}
                {u.hypotheses.length > 0 && <> ({u.hypotheses.join(', ')})</>}
              </li>
            ))}
            {result.legal_uncertainty.length === 0 && <li style={emptyStateStyle}>None flagged.</li>}
          </ul>

          <h3>Counterarguments</h3>
          {result.counterarguments.map((w, i) => {
            const sev = w.severity ?? 'unspecified'
            return (
              <div key={i} style={cardStyle}>
                <span style={badgeStyle(severityColor[sev], severityBg[sev])}>{sev}</span>
                <p style={{ marginTop: '0.35rem', fontSize: '0.88rem', color: colors.text }}>{w.description}</p>
              </div>
            )
          })}
          {result.counterarguments.length === 0 && <p style={emptyStateStyle}>None flagged.</p>}

          {result.flagged_conflicts.length > 0 && (
            <>
              <h3>Unresolved tension between agents</h3>
              {result.flagged_conflicts.map((c, i) => (
                <div key={i} style={{ ...calloutStyle.danger, marginBottom: '0.5rem' }}>
                  {c.description}
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </section>
  )
}
