import { useEffect, useState } from 'react'
import { api, type QuestionPreparationResult } from '../api'
import { PanelHeader } from './PanelHeader'
import { buttonStyle, cardStyle, colors, disabledStyle, emptyStateStyle, panelStyle, tagStyle } from './shared'

export function QuestionPreparationPanel({ caseId, triggerSignal = 0 }: { caseId: string; triggerSignal?: number }) {
  const [result, setResult] = useState<QuestionPreparationResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function run() {
    setLoading(true)
    try {
      setResult(await api.prepareQuestions(caseId))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (triggerSignal > 0) run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggerSignal])

  return (
    <section style={panelStyle}>
      <PanelHeader icon="❓" title="Question & Answer Preparation" subtitle="Likely questions, and only the responses your known facts can actually support." />
      <button style={{ ...buttonStyle, marginTop: '0.9rem', ...disabledStyle(loading) }} onClick={run} disabled={loading}>
        {loading ? 'Preparing…' : 'Prepare questions'}
      </button>

      {result?.insufficient_case_state && <p style={{ ...emptyStateStyle, marginTop: '0.75rem' }}>Not enough case information yet.</p>}

      {result && !result.insufficient_case_state && (
        <div style={{ marginTop: '0.5rem' }}>
          {(result.questions ?? []).map((q, i) => (
            <div key={i} style={cardStyle}>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <span style={tagStyle}>{q.source}</span>
              </div>
              <p style={{ marginTop: '0.4rem', color: colors.text, fontWeight: 500 }}>{q.question}</p>
              {q.suggested_response ? (
                <p style={{ marginTop: '0.35rem', fontSize: '0.87rem' }}>Suggested response: {q.suggested_response}</p>
              ) : (
                <p style={{ marginTop: '0.35rem', fontSize: '0.85rem', color: colors.warn }}>Not yet answerable: {q.gap_note}</p>
              )}
            </div>
          ))}
          {(result.questions ?? []).length === 0 && <p style={emptyStateStyle}>No questions generated.</p>}
        </div>
      )}
    </section>
  )
}
