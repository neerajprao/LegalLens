import { useState } from 'react'
import { api, type QuestionPreparationResult } from '../api'
import { buttonStyle, panelStyle } from './shared'

export function QuestionPreparationPanel({ caseId }: { caseId: string }) {
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

  return (
    <section style={panelStyle}>
      <h2>Question &amp; Answer Preparation</h2>
      <button style={buttonStyle} onClick={run} disabled={loading}>
        {loading ? 'Preparing…' : 'Prepare questions'}
      </button>

      {result?.insufficient_case_state && <p>Not enough case information yet.</p>}

      {result && !result.insufficient_case_state && (
        <ul style={{ marginTop: '0.75rem' }}>
          {result.questions.map((q, i) => (
            <li key={i} style={{ marginBottom: '0.5rem' }}>
              <strong>[{q.source}]</strong> {q.question}
              <br />
              {q.suggested_response ? (
                <span>Suggested response: {q.suggested_response}</span>
              ) : (
                <span style={{ color: '#b7791f' }}>Not yet answerable: {q.gap_note}</span>
              )}
            </li>
          ))}
          {result.questions.length === 0 && <li>No questions generated.</li>}
        </ul>
      )}
    </section>
  )
}
