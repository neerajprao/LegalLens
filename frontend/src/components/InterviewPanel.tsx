import { useState } from 'react'
import { api, type InterviewQuestionResult } from '../api'
import { buttonStyle, panelStyle } from './shared'

export function InterviewPanel({ caseId, onAnswered }: { caseId: string; onAnswered: () => void }) {
  const [current, setCurrent] = useState<InterviewQuestionResult | null>(null)
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const [contradictionNotice, setContradictionNotice] = useState<string | null>(null)

  async function fetchNext() {
    setLoading(true)
    setContradictionNotice(null)
    try {
      const result = await api.nextInterviewQuestion(caseId)
      setCurrent(result)
      setAnswer('')
    } finally {
      setLoading(false)
    }
  }

  async function submitAnswer() {
    if (!current?.turn_id || !answer.trim()) return
    setLoading(true)
    try {
      const result = await api.submitInterviewAnswer(caseId, current.turn_id, answer)
      if (result.contradiction_found) {
        setContradictionNotice(result.contradiction_explanation)
      }
      onAnswered()
      await fetchNext()
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={panelStyle}>
      <h2>Interview</h2>
      {!current && (
        <button style={buttonStyle} onClick={fetchNext} disabled={loading}>
          {loading ? 'Loading…' : 'Get next question'}
        </button>
      )}

      {current?.sufficient && (
        <p>
          <em>Interview complete for now.</em> {current.sufficiency_reason && `(${current.sufficiency_reason})`}
        </p>
      )}

      {current && !current.sufficient && current.next_question && (
        <div>
          <p style={{ fontWeight: 600 }}>{current.next_question}</p>
          {current.rationale && <p style={{ color: '#666', fontSize: '0.9em' }}>Why this matters: {current.rationale}</p>}
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            rows={3}
            style={{ width: '100%' }}
            placeholder="Your answer..."
          />
          <div style={{ marginTop: '0.5rem' }}>
            <button style={buttonStyle} onClick={submitAnswer} disabled={loading || !answer.trim()}>
              {loading ? 'Submitting…' : 'Submit answer'}
            </button>
          </div>
        </div>
      )}

      {contradictionNotice && (
        <p style={{ background: '#fff3cd', padding: '0.5rem', borderRadius: 4, marginTop: '0.5rem' }}>
          Warning: this answer may contradict something said earlier — {contradictionNotice}
        </p>
      )}
    </section>
  )
}
