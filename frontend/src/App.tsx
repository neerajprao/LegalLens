import { useEffect, useState } from 'react'
import { api } from './api'
import { AuditLogPanel } from './components/AuditLogPanel'
import { CaseStrengthPanel } from './components/CaseStrengthPanel'
import { ChatPanel } from './components/ChatPanel'
import { ClaimsEvidencePanel } from './components/ClaimsEvidencePanel'
import { ClassificationPanel } from './components/ClassificationPanel'
import { DevilsAdvocatePanel } from './components/DevilsAdvocatePanel'
import { DocumentsPanel } from './components/DocumentsPanel'
import { QuestionPreparationPanel } from './components/QuestionPreparationPanel'
import {
  buttonStyle,
  calloutStyle,
  colors,
  disabledStyle,
  eyebrowStyle,
  mono,
  panelStyle,
  secondaryButtonStyle,
  tabBarStyle,
  tabButtonStyle,
  tagStyle,
} from './components/shared'
import { StrategyPanel } from './components/StrategyPanel'
import { TimelinePanel } from './components/TimelinePanel'

const STAGES = [
  { id: 'interview', label: 'Interview', number: 1 },
  { id: 'dashboard', label: 'Case Dashboard', number: 2 },
  { id: 'review', label: 'Document Review', number: 3 },
] as const

type StageId = (typeof STAGES)[number]['id']

const STORAGE_KEY_CASE_ID = 'legallens_case_id'
const STORAGE_KEY_FACTS_SUBMITTED = 'legallens_facts_submitted'
const STORAGE_KEY_STAGE = 'legallens_stage'

function App() {
  const [caseId, setCaseId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [factsSubmitted, setFactsSubmitted] = useState(false)
  const [stage, setStage] = useState<StageId>('interview')
  const [starting, setStarting] = useState(false)
  const [restoring, setRestoring] = useState(true)

  // "Analyze the case" runs every dashboard agent (evidence gaps, classification, devil's
  // advocate, strategy, question prep) at once — analyzeSignal is bumped to tell each panel's own
  // effect to fire (see each panel's triggerSignal prop), without touching any panel's individual
  // button. caseStale tracks whether the last analysis run still reflects the current claims and
  // evidence: it starts true (nothing has been analyzed yet), goes false right when Analyze is
  // clicked, and flips back to true the moment ClaimsEvidencePanel reports a claim or evidence
  // change — that's the "clickable again after any change" requirement.
  const [analyzeSignal, setAnalyzeSignal] = useState(0)
  const [caseStale, setCaseStale] = useState(true)

  // Resume the last active case on load (page refresh, browser reopen) instead of always
  // starting blank — the case itself already lives in the backend; this just remembers which
  // one to point the UI at. Validated against the backend rather than trusted blindly, since
  // the remembered id could be stale (e.g. a reset dev database).
  useEffect(() => {
    const storedCaseId = localStorage.getItem(STORAGE_KEY_CASE_ID)
    if (!storedCaseId) {
      setRestoring(false)
      return
    }
    api
      .getCase(storedCaseId)
      .then((data) => {
        if (data.error) {
          localStorage.removeItem(STORAGE_KEY_CASE_ID)
          localStorage.removeItem(STORAGE_KEY_FACTS_SUBMITTED)
          localStorage.removeItem(STORAGE_KEY_STAGE)
          return
        }
        setCaseId(storedCaseId)
        setFactsSubmitted(localStorage.getItem(STORAGE_KEY_FACTS_SUBMITTED) === 'true')
        const storedStage = localStorage.getItem(STORAGE_KEY_STAGE)
        if (storedStage === 'interview' || storedStage === 'dashboard' || storedStage === 'review') {
          setStage(storedStage)
        }
      })
      .catch(() => {
        // Backend unreachable on load — leave the stored id alone and let the user retry rather
        // than discarding a reference that may still be valid once the backend comes back.
      })
      .finally(() => setRestoring(false))
  }, [])

  useEffect(() => {
    if (caseId) localStorage.setItem(STORAGE_KEY_CASE_ID, caseId)
  }, [caseId])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY_FACTS_SUBMITTED, String(factsSubmitted))
  }, [factsSubmitted])

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY_STAGE, stage)
  }, [stage])

  async function startCase() {
    setError(null)
    setStarting(true)
    try {
      const data = await api.createCase()
      setCaseId(data.id)
    } catch {
      setError('Could not start a case. Is the backend running on :8000?')
    } finally {
      setStarting(false)
    }
  }

  function startNewCase() {
    const confirmed = window.confirm(
      "Start a new case? Your current case's data stays saved on the backend, but this page will no longer point at it."
    )
    if (!confirmed) return
    localStorage.removeItem(STORAGE_KEY_CASE_ID)
    localStorage.removeItem(STORAGE_KEY_FACTS_SUBMITTED)
    localStorage.removeItem(STORAGE_KEY_STAGE)
    setCaseId(null)
    setFactsSubmitted(false)
    setStage('interview')
    setError(null)
    setAnalyzeSignal(0)
    setCaseStale(true)
  }

  function analyzeCase() {
    setCaseStale(false)
    setAnalyzeSignal((s) => s + 1)
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header
        style={{
          borderBottom: `1px solid ${colors.border}`,
          background: 'rgba(10,11,13,0.7)',
          backdropFilter: 'blur(10px)',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <div
          style={{
            maxWidth: 1080,
            margin: '0 auto',
            padding: '1.1rem 1.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <span
              style={{
                width: 32,
                height: 32,
                borderRadius: 6,
                background: colors.goldSoft,
                border: `1px solid ${colors.goldBorder}`,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1rem',
              }}
            >
              ⚖️
            </span>
            <div>
              <div style={{ fontFamily: 'var(--serif)', fontWeight: 700, fontSize: '1.1rem', letterSpacing: '-0.01em' }}>
                LEGAL LENS
              </div>
              <div style={{ ...eyebrowStyle, color: colors.goldBright, fontSize: '0.62rem' }}>AI Case Intelligence</div>
            </div>
          </div>
          {caseId && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.7rem' }}>
              <span style={tagStyle}>
                CASE <span style={{ color: colors.textFaint, margin: '0 0.3rem' }}>//</span>
                <code>{caseId.slice(0, 8).toUpperCase()}</code>
              </span>
              <button style={{ ...secondaryButtonStyle, padding: '0.4rem 0.75rem', fontSize: '0.78rem' }} onClick={startNewCase}>
                Start new case
              </button>
            </div>
          )}
        </div>
      </header>

      <main style={{ maxWidth: 1080, margin: '0 auto', padding: '1.75rem 1.5rem 4rem', width: '100%', flex: 1 }}>
        <div style={calloutStyle.warn}>
          <div style={{ ...eyebrowStyle, color: colors.warn, marginBottom: '0.3rem' }}>Early development build</div>
          This is not legal advice. All output is AI-generated and requires professional review before reliance.
        </div>

        {error && <div style={{ ...calloutStyle.danger, marginTop: '1rem' }}>{error}</div>}

        {restoring ? (
          <section style={{ ...panelStyle, textAlign: 'center', padding: '3rem 2rem', color: colors.textFaint }}>
            Restoring your case…
          </section>
        ) : !caseId ? (
          <section style={{ ...panelStyle, textAlign: 'center', padding: '3rem 2rem' }}>
            <div style={{ ...eyebrowStyle, color: colors.goldBright, marginBottom: '0.9rem' }}>
              Legal Intelligence Platform · India — Karnataka
            </div>
            <h1 style={{ fontSize: '2rem', marginBottom: '0.6rem' }}>Turn a legal situation into a structured case.</h1>
            <p style={{ maxWidth: 480, margin: '0 auto 1.5rem', color: colors.textDim }}>
              Describe what happened, and Legal Lens will help you organize facts, evidence, applicable law, and
              next steps — all with traceable sources.
            </p>
            <button style={{ ...buttonStyle, ...disabledStyle(starting) }} onClick={startCase} disabled={starting}>
              {starting ? 'Starting…' : 'Start a case →'}
            </button>
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                flexWrap: 'wrap',
                gap: '0.5rem 1.4rem',
                marginTop: '1.75rem',
                paddingTop: '1.5rem',
                borderTop: `1px solid ${colors.borderSoft}`,
              }}
            >
              {['9 SPECIALIST AGENTS', '5,136 LEGAL TEXT CHUNKS', 'LOCAL MODEL', 'RAG-GROUNDED RETRIEVAL'].map((m) => (
                <span key={m} style={{ fontFamily: mono, fontSize: '0.68rem', letterSpacing: '0.06em', color: colors.textFaint }}>
                  {m}
                </span>
              ))}
            </div>
          </section>
        ) : (
          <nav style={tabBarStyle}>
            {STAGES.map((s) => {
              const enabled = s.id === 'interview' || factsSubmitted
              return (
                <button
                  key={s.id}
                  style={tabButtonStyle(stage === s.id, enabled)}
                  onClick={() => enabled && setStage(s.id)}
                  disabled={!enabled}
                >
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 18,
                      height: 18,
                      borderRadius: 3,
                      fontSize: '0.65rem',
                      marginRight: '0.5rem',
                      background: stage === s.id ? colors.goldSoft : 'rgba(255,255,255,0.06)',
                      border: `1px solid ${stage === s.id ? colors.goldBorder : colors.border}`,
                    }}
                  >
                    0{s.number}
                  </span>
                  {s.label}
                </button>
              )
            })}
          </nav>
        )}

        {/* Each stage, once mounted, stays mounted for the rest of the session (hidden via CSS
            rather than removed) so switching tabs never wipes a panel's own state — the chat
            transcript especially, which used to reset to just the opening line on every tab
            switch since the whole component was being unmounted and remounted. */}
        {caseId && (
          <div style={{ display: stage === 'interview' ? 'block' : 'none' }}>
            <ChatPanel caseId={caseId} onFirstNarrative={() => setFactsSubmitted(true)} />

            {factsSubmitted && (
              <>
                <TimelinePanel caseId={caseId} />
                <div style={{ marginTop: '1.25rem', textAlign: 'right' }}>
                  <button style={secondaryButtonStyle} onClick={() => setStage('dashboard')}>
                    Continue to Case Dashboard →
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {caseId && factsSubmitted && (
          <div style={{ display: stage === 'dashboard' ? 'block' : 'none' }}>
            <ClaimsEvidencePanel caseId={caseId} triggerSignal={analyzeSignal} onCaseChanged={() => setCaseStale(true)} />

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '1rem',
                flexWrap: 'wrap',
                marginTop: '1.25rem',
                padding: '1rem 1.25rem',
                background: colors.surface,
                border: `1px solid ${colors.border}`,
                borderRadius: 10,
              }}
            >
              <div>
                <div style={{ ...eyebrowStyle, color: colors.goldBright, marginBottom: '0.2rem' }}>Run every agent at once</div>
                <p style={{ fontSize: '0.84rem', color: colors.textDim, maxWidth: 520 }}>
                  {caseStale
                    ? 'Once your claims and evidence above are ready, analyze the case to run evidence gaps, classification, devil\'s advocate, strategy, and question prep together. Each panel below also has its own button if you just want to re-run one.'
                    : "Analyzed against your current claims and evidence. Add, edit, or remove a claim or evidence item to make this clickable again — or re-run any single agent below."}
                </p>
              </div>
              <button style={{ ...buttonStyle, ...disabledStyle(!caseStale) }} onClick={analyzeCase} disabled={!caseStale}>
                {caseStale ? 'Analyze the case →' : 'Analyzed — up to date'}
              </button>
            </div>

            <ClassificationPanel caseId={caseId} triggerSignal={analyzeSignal} />
            <DevilsAdvocatePanel caseId={caseId} triggerSignal={analyzeSignal} />
            <StrategyPanel caseId={caseId} triggerSignal={analyzeSignal} />
            <QuestionPreparationPanel caseId={caseId} triggerSignal={analyzeSignal} />
          </div>
        )}

        {caseId && factsSubmitted && (
          <div style={{ display: stage === 'review' ? 'block' : 'none' }}>
            <DocumentsPanel caseId={caseId} />
            <CaseStrengthPanel caseId={caseId} />
            <AuditLogPanel caseId={caseId} />
          </div>
        )}
      </main>

      <footer
        style={{
          borderTop: `1px solid ${colors.border}`,
          padding: '1.25rem 1.5rem',
          textAlign: 'center',
          fontSize: '0.76rem',
          color: colors.textFaint,
        }}
      >
        Legal Lens is a case-preparation aid, not a lawyer. It does not file documents, predict outcomes, or
        replace professional legal advice.
        <div style={{ ...eyebrowStyle, marginTop: '0.6rem', fontSize: '0.6rem' }}>
          Legal Lens · AI-Assisted Case Preparation · Portfolio / Development Project
        </div>
      </footer>
    </div>
  )
}

export default App
