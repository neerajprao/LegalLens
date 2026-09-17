import { useEffect, useState } from 'react'
import { API_BASE, api, type ClassifyResult, type ProvisionMetadata } from '../api'
import { PanelHeader } from './PanelHeader'
import { badgeStyle, buttonStyle, calloutStyle, cardStyle, colors, disabledStyle, emptyStateStyle, ghostButtonStyle, mono, panelStyle } from './shared'

const CONFIDENCE_COLOR: Record<string, string> = {
  high: colors.ok,
  medium: colors.warn,
  low: colors.textFaint,
}

// The backend now bakes a real highlight annotation onto the provision's own text (see
// app/pdf_highlight.py) rather than relying on the browser's native "find in page" overlay —
// the old "#page=N&search=term" fragment approach only worked in Chromium and only ever
// highlighted the short title string, not the actual explanatory passage. `section`/`page` are
// sent as query params so the backend can render that copy; `#page=N` is kept as a URL fragment
// too so the viewer still opens scrolled to the right page immediately, without waiting on
// where the highlight itself ends up.
function sourceDocumentUrl(meta: ProvisionMetadata): string {
  const file = encodeURIComponent(meta.source_file || '')
  const page = meta.page_number && meta.page_number > 0 ? meta.page_number : 1
  const params = new URLSearchParams({ page: String(page) })
  if (meta.section_number) params.set('section', meta.section_number)
  return `${API_BASE}/documents/${file}?${params.toString()}#page=${page}`
}

function ProvisionCard({ hit }: { hit: { text: string; metadata: ProvisionMetadata; distance: number } }) {
  const [expanded, setExpanded] = useState(false)
  const meta = hit.metadata
  const gist = meta.section_title || 'No title available for this provision.'
  const preview = hit.text.length > 220 && !expanded ? `${hit.text.slice(0, 220).trimEnd()}…` : hit.text

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem' }}>
        <code>
          {meta.act_name} §{meta.section_number}
        </code>
        {meta.page_number > 0 && (
          <a
            href={sourceDocumentUrl(meta)}
            target="_blank"
            rel="noreferrer"
            style={{ ...ghostButtonStyle, textDecoration: 'none', fontFamily: mono, fontSize: '0.72rem' }}
          >
            View in source, p.{meta.page_number} →
          </a>
        )}
      </div>
      <p style={{ fontSize: '0.92rem', marginTop: '0.4rem', fontWeight: 600, color: colors.text }}>{gist}</p>
      <p style={{ fontSize: '0.85rem', marginTop: '0.3rem', color: colors.textDim, lineHeight: 1.55 }}>{preview}</p>
      {hit.text.length > 220 && (
        <button
          style={{ ...ghostButtonStyle, marginTop: '0.4rem', padding: '0.2rem 0.5rem' }}
          onClick={() => setExpanded((e) => !e)}
        >
          {expanded ? 'Show less' : 'Show full text'}
        </button>
      )}
    </div>
  )
}

export function ClassificationPanel({ caseId, triggerSignal = 0 }: { caseId: string; triggerSignal?: number }) {
  const [result, setResult] = useState<ClassifyResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function run() {
    setLoading(true)
    try {
      setResult(await api.classify(caseId))
    } finally {
      setLoading(false)
    }
  }

  // Bumped by the "Analyze the case" button in App.tsx so this agent runs alongside every other
  // one — skipped on mount (triggerSignal starts at 0) so this never fires before the user asks.
  useEffect(() => {
    if (triggerSignal > 0) run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggerSignal])

  return (
    <section style={panelStyle}>
      <PanelHeader
        icon="⚖️"
        title="Legal Classification & Law Retrieval"
        subtitle="Candidate legal categories, and the statutory provisions actually retrieved to support them — never invented."
      />
      <button style={{ ...buttonStyle, marginTop: '0.9rem', ...disabledStyle(loading) }} onClick={run} disabled={loading}>
        {loading ? 'Running…' : 'Classify and retrieve provisions'}
      </button>

      {result && (
        <div style={{ marginTop: '0.5rem' }}>
          <h3>Candidate categories (hypotheses, not conclusions)</h3>
          {result.classification.hypotheses.length === 0 && <p style={emptyStateStyle}>No hypotheses could be formed yet.</p>}
          {result.classification.hypotheses.map((h, i) => (
            <div key={i} style={cardStyle}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem' }}>
                <strong style={{ color: colors.text }}>{h.category}</strong>
                <span style={badgeStyle(CONFIDENCE_COLOR[h.confidence] ?? colors.textFaint, 'rgba(255,255,255,0.05)')}>
                  {h.confidence}
                </span>
              </div>
              <p style={{ fontSize: '0.88rem', marginTop: '0.3rem' }}>{h.rationale}</p>
            </div>
          ))}

          <h3>Retrieved provisions</h3>
          {result.retrieval.insufficient_data ? (
            <div style={calloutStyle.warn}>{result.retrieval.note || 'No verified provisions found for these hypotheses.'}</div>
          ) : (
            Object.entries(result.retrieval.retrieved).map(([category, hits]) => (
              <div key={category} style={{ marginBottom: '0.75rem' }}>
                <p style={{ fontWeight: 600, color: colors.textDim, fontSize: '0.85rem' }}>{category}</p>
                {hits.map((hit, i) => (
                  <ProvisionCard key={i} hit={hit} />
                ))}
              </div>
            ))
          )}
        </div>
      )}
    </section>
  )
}
