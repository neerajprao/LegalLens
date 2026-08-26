import { useState } from 'react'
import './App.css'
import { api, type FactExtractionResult } from './api'
import { AuditLogPanel } from './components/AuditLogPanel'
import { CaseStrengthPanel } from './components/CaseStrengthPanel'
import { ClaimsEvidencePanel } from './components/ClaimsEvidencePanel'
import { ClassificationPanel } from './components/ClassificationPanel'
import { DevilsAdvocatePanel } from './components/DevilsAdvocatePanel'
import { DocumentsPanel } from './components/DocumentsPanel'
import { InterviewPanel } from './components/InterviewPanel'
import { QuestionPreparationPanel } from './components/QuestionPreparationPanel'
import { StrategyPanel } from './components/StrategyPanel'
import { TimelinePanel } from './components/TimelinePanel'

function App() {
  const [caseId, setCaseId] = useState<string | null>(null)
  const [narrative, setNarrative] = useState('')
  const [factResult, setFactResult] = useState<FactExtractionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [factsSubmitted, setFactsSubmitted] = useState(false)

  async function startCase() {
    setError(null)
    try {
      const data = await api.createCase()
      setCaseId(data.id)
    } catch {
      setError('Could not start a case. Is the backend running on :8000?')
    }
  }

  async function submitNarrative() {
    if (!caseId || !narrative.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await api.submitNarrative(caseId, narrative)
      setFactResult(data.fact_extraction)
      setFactsSubmitted(true)
    } catch {
      setError('Fact extraction failed. Check the backend logs and ANTHROPIC_API_KEY.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ maxWidth: 860, margin: '2rem auto', padding: '0 1rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1>Legal Lens</h1>
      <p style={{ background: '#fff3cd', padding: '0.75rem', borderRadius: 6 }}>
        This is an early development build. Nothing here is legal advice — all output is an
        AI-generated draft that requires professional review before any reliance on it.
      </p>

      {!caseId ? (
        <button onClick={startCase}>Start a case</button>
      ) : (
        <p>
          Case started: <code>{caseId}</code>
        </p>
      )}

      {caseId && !factsSubmitted && (
        <>
          <textarea
            value={narrative}
            onChange={(e) => setNarrative(e.target.value)}
            placeholder="Describe your situation in your own words..."
            rows={8}
            style={{ width: '100%', marginTop: '1rem' }}
          />
          <div style={{ marginTop: '0.5rem' }}>
            <button onClick={submitNarrative} disabled={loading || !narrative.trim()}>
              {loading ? 'Extracting facts…' : 'Submit'}
            </button>
          </div>
        </>
      )}

      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {factResult && (
        <section style={{ marginTop: '1.5rem' }}>
          <h2>Extracted statements</h2>
          <ul>
            {(factResult.statements ?? []).map((s, i) => (
              <li key={i}>
                <strong>[{s.classification}]</strong> {s.raw_text}
              </li>
            ))}
          </ul>
          <h2>Extracted events</h2>
          <ul>
            {(factResult.events ?? []).map((e, i) => (
              <li key={i}>
                {e.description} {e.occurred_at && `(${e.occurred_at}${e.is_approximate_date ? ', approximate' : ''})`}
              </li>
            ))}
          </ul>
        </section>
      )}

      {caseId && factsSubmitted && (
        <>
          <InterviewPanel caseId={caseId} onAnswered={() => {}} />
          <TimelinePanel caseId={caseId} />
          <ClaimsEvidencePanel caseId={caseId} />
          <ClassificationPanel caseId={caseId} />
          <DevilsAdvocatePanel caseId={caseId} />
          <StrategyPanel caseId={caseId} />
          <QuestionPreparationPanel caseId={caseId} />
          <DocumentsPanel caseId={caseId} />
          <CaseStrengthPanel caseId={caseId} />
          <AuditLogPanel caseId={caseId} />
        </>
      )}
    </main>
  )
}

export default App
