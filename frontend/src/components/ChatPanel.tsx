import { useEffect, useRef, useState } from 'react'
import { api, type FactExtractionResult } from '../api'
import { PanelHeader } from './PanelHeader'
import { buttonStyle, calloutStyle, colors, disabledStyle, ghostButtonStyle, inputStyle } from './shared'

type NarrativeAuditPayload = { narrative?: string; fact_extraction_result?: FactExtractionResult }

// What produced a given user message — needed so an edit-and-resend knows which backend call to
// repeat. Greeting replies and any message reconstructed from a shape we don't recognize get no
// meta at all, which makes them non-editable (see isEditable below) rather than risking a resend
// against the wrong endpoint.
type UserMessageMeta = { kind: 'narrative' } | { kind: 'answer'; turnId: string }

// One past or current version of an edited message: its own text, plus everything that was said
// after it (its "tail") and the pendingTurnId that resulted from it — recorded so switching back
// to an older version restores the interview's pending-question state exactly, not just the text.
type MessageVersion = { text: string; tail: ChatMessage[]; pendingTurnId: string | null }

type ChatMessage = {
  id: string
  role: 'assistant' | 'user' | 'note'
  text: string
  sub?: string
  meta?: UserMessageMeta
  versions?: MessageVersion[]
  activeVersion?: number
}

const GREETING_RE =
  /^\s*(hi+|hello+|hey+|yo|sup|good\s*(morning|afternoon|evening)|what'?s up)(\s+(there|friend|again))?[\s!.?]*$/i

function isGreeting(text: string): boolean {
  return GREETING_RE.test(text)
}

function uid(): string {
  return Math.random().toString(36).slice(2)
}

const OPENING_MESSAGE =
  "Hello! I'm Legal Lens. I can help you organize the facts of your situation, spot what evidence is missing, and " +
  'find the law that might apply. Whenever you\'re ready, tell me in your own words what happened.'

const GREETING_REPLY =
  "Hello — how can I help you today? Whenever you're ready, describe what happened: who was involved, roughly " +
  'when, and what occurred.'

const NO_DETAIL_NUDGE =
  "I couldn't pick out any concrete details from that. Could you tell me more — who was involved, what happened, and roughly when and where? Specific details like dates, names, or amounts help too."

const EDITED_NARRATIVE_NOTE =
  'Edited opening message resubmitted — any new facts found in it are added alongside what was already extracted from the original text, not in place of it.'

function hasFacts(result: FactExtractionResult): boolean {
  return (result.statements?.length ?? 0) > 0 || (result.events?.length ?? 0) > 0
}

function summarizeExtraction(result: FactExtractionResult): string | undefined {
  const statements = result.statements?.length ?? 0
  const events = result.events?.length ?? 0
  if (!statements && !events) return undefined
  const parts = []
  if (statements) parts.push(`${statements} statement${statements === 1 ? '' : 's'}`)
  if (events) parts.push(`${events} event${events === 1 ? '' : 's'}`)
  return `Noted ${parts.join(' and ')} from that.`
}

function sufficiencyMessage(sufficiencyReason: string): ChatMessage {
  return {
    id: uid(),
    role: 'assistant',
    text: sufficiencyReason
      ? `Thanks — I think I have enough for now (${sufficiencyReason}). You can add more any time, or continue to the Case Dashboard when you're ready.`
      : "Thanks — I have enough to work with for now. You can add more any time, or continue to the Case Dashboard when you're ready.",
  }
}

export function ChatPanel({ caseId, onFirstNarrative }: { caseId: string; onFirstNarrative: () => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([{ id: uid(), role: 'assistant', text: OPENING_MESSAGE }])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [hydrating, setHydrating] = useState(true)
  const [narrativeStarted, setNarrativeStarted] = useState(false)
  const [pendingTurnId, setPendingTurnId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editText, setEditText] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  // Rebuild the conversation from what the backend actually has on record (audit log entries
  // for each submitted narrative, plus the interview turns) whenever this component mounts —
  // covers both a page reload and a first-ever mount after switching into this tab. The chat
  // transcript itself is never the source of truth; this is a reconstruction of it.
  useEffect(() => {
    let cancelled = false

    async function hydrate() {
      setHydrating(true)
      try {
        const [auditResult, turnsResult] = await Promise.all([api.auditLog(caseId), api.interviewTurns(caseId)])
        if (cancelled) return

        type TimelineItem =
          | { at: string; kind: 'narrative'; narrative: string; extraction: FactExtractionResult }
          | { kind: 'turn'; at: string; turn: (typeof turnsResult.turns)[number] }

        const narrativeItems: TimelineItem[] = auditResult.entries
          .filter((e) => e.event_type === 'narrative_submitted')
          .map((e) => {
            const payload = e.payload as NarrativeAuditPayload
            return {
              kind: 'narrative' as const,
              at: e.created_at,
              narrative: payload.narrative ?? '',
              extraction: payload.fact_extraction_result ?? {},
            }
          })
        const turnItems: TimelineItem[] = turnsResult.turns.map((turn) => ({ kind: 'turn' as const, at: turn.created_at, turn }))

        const timeline = [...narrativeItems, ...turnItems].sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime())

        if (timeline.length === 0) {
          setMessages([{ id: uid(), role: 'assistant', text: OPENING_MESSAGE }])
          setNarrativeStarted(false)
          setPendingTurnId(null)
          return
        }

        const rebuilt: ChatMessage[] = [{ id: uid(), role: 'assistant', text: OPENING_MESSAGE }]
        let anyFacts = false
        let lastPendingTurnId: string | null = null

        for (const item of timeline) {
          if (item.kind === 'narrative') {
            rebuilt.push({ id: uid(), role: 'user', text: item.narrative, meta: { kind: 'narrative' } })
            if (hasFacts(item.extraction)) {
              anyFacts = true
              const summary = summarizeExtraction(item.extraction)
              if (summary) rebuilt.push({ id: uid(), role: 'note', text: summary })
            } else {
              rebuilt.push({ id: uid(), role: 'assistant', text: NO_DETAIL_NUDGE })
            }
          } else {
            const { turn } = item
            rebuilt.push({
              id: uid(),
              role: 'assistant',
              text: turn.question,
              sub: turn.rationale ? `Why I'm asking: ${turn.rationale}` : undefined,
            })
            if (turn.answer) {
              rebuilt.push({ id: uid(), role: 'user', text: turn.answer, meta: { kind: 'answer', turnId: turn.turn_id } })
              if (turn.contradicts_ref) {
                rebuilt.push({
                  id: uid(),
                  role: 'note',
                  text: turn.contradicts_text
                    ? `This may contradict something said earlier — "${turn.contradicts_text}". ${turn.contradiction_explanation}`
                    : `This may contradict something said earlier — ${turn.contradiction_explanation}`,
                })
              }
              lastPendingTurnId = null
            } else {
              lastPendingTurnId = turn.turn_id
            }
          }
        }

        setMessages(rebuilt)
        const started = anyFacts || turnsResult.turns.length > 0
        setNarrativeStarted(started)
        setPendingTurnId(lastPendingTurnId)
        if (started) onFirstNarrative()
      } catch {
        // Hydration failing (e.g. backend briefly unreachable) shouldn't block using the chat —
        // fall back to a fresh conversation rather than leaving the panel stuck loading.
        if (!cancelled) {
          setMessages([{ id: uid(), role: 'assistant', text: OPENING_MESSAGE }])
        }
      } finally {
        if (!cancelled) setHydrating(false)
      }
    }

    hydrate()
    return () => {
      cancelled = true
    }
  }, [caseId])

  // Asks for (and renders) the next interview question, or the wrap-up message if the interview
  // is done. Returns the resulting pendingTurnId alongside the message(s) so callers building a
  // version record (see handleEditSave) can store it for exact restoration later.
  async function nextQuestionMessages(): Promise<{ messages: ChatMessage[]; pendingTurnId: string | null }> {
    const result = await api.nextInterviewQuestion(caseId)
    if (result.sufficient || !result.next_question) {
      return { pendingTurnId: null, messages: [sufficiencyMessage(result.sufficiency_reason)] }
    }
    return {
      pendingTurnId: result.turn_id,
      messages: [{ id: uid(), role: 'assistant', text: result.next_question, sub: result.rationale ? `Why I'm asking: ${result.rationale}` : undefined }],
    }
  }

  // Submits (or resubmits) the opening narrative and returns everything that follows from it —
  // the source of truth for both a normal send and an edit-and-resend of that same message.
  async function narrativeFlow(text: string): Promise<{ messages: ChatMessage[]; pendingTurnId: string | null }> {
    const narrativeResult = await api.submitNarrative(caseId, text)
    const extraction = narrativeResult.fact_extraction

    if (!hasFacts(extraction)) {
      // Nothing was actually extracted — never hand this off to the interview loop, since an
      // empty case state has previously led to a spurious "sufficient" verdict. Ask for
      // specifics instead of silently treating small talk as a completed intake.
      return { pendingTurnId: null, messages: [{ id: uid(), role: 'assistant', text: NO_DETAIL_NUDGE }] }
    }

    if (!narrativeStarted) {
      setNarrativeStarted(true)
      onFirstNarrative()
    }
    const tail: ChatMessage[] = []
    const summary = summarizeExtraction(extraction)
    if (summary) tail.push({ id: uid(), role: 'note', text: summary })
    const next = await nextQuestionMessages()
    tail.push(...next.messages)
    return { pendingTurnId: next.pendingTurnId, messages: tail }
  }

  // Submits (or resubmits) an answer to an interview turn and returns everything that follows.
  async function answerFlow(turnId: string, text: string): Promise<{ messages: ChatMessage[]; pendingTurnId: string | null }> {
    const answerResult = await api.submitInterviewAnswer(caseId, turnId, text)
    const tail: ChatMessage[] = []
    if (answerResult.contradiction_found) {
      tail.push({
        id: uid(),
        role: 'note',
        text: answerResult.contradicts_text
          ? `This may contradict something said earlier — "${answerResult.contradicts_text}". ${answerResult.contradiction_explanation}`
          : `This may contradict something said earlier — ${answerResult.contradiction_explanation}`,
      })
    }
    const next = await nextQuestionMessages()
    tail.push(...next.messages)
    return { pendingTurnId: next.pendingTurnId, messages: tail }
  }

  async function handleSend() {
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    setError(null)

    const isGreetingMsg = !narrativeStarted && !pendingTurnId && isGreeting(text)
    const userMsg: ChatMessage = {
      id: uid(),
      role: 'user',
      text,
      // Greetings aren't resendable against any real endpoint, so they get no meta — and
      // therefore no edit affordance (see isEditable).
      meta: isGreetingMsg ? undefined : pendingTurnId ? { kind: 'answer', turnId: pendingTurnId } : { kind: 'narrative' },
    }
    setMessages((m) => [...m, userMsg])
    setSending(true)
    try {
      if (isGreetingMsg) {
        setMessages((m) => [...m, { id: uid(), role: 'assistant', text: GREETING_REPLY }])
        return
      }

      const { messages: tail, pendingTurnId: nextPending } = pendingTurnId
        ? await answerFlow(pendingTurnId, text)
        : await narrativeFlow(text)
      setPendingTurnId(nextPending)
      setMessages((m) => [...m, ...tail])
    } catch {
      setError('Something went wrong reaching the backend. Check that it is running and try again.')
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function startEdit(msg: ChatMessage) {
    setEditingId(msg.id)
    setEditText(msg.text)
  }

  function cancelEdit() {
    setEditingId(null)
    setEditText('')
  }

  // Edits and resends ONLY the message being edited — never the rest of the conversation. The
  // pre-edit text (and everything that had followed it) is kept as a version so the user can
  // flip back to what was originally said/asked, ChatGPT-style ("1/2" pager on the message).
  async function handleEditSave(msg: ChatMessage) {
    const newText = editText.trim()
    if (!newText || !msg.meta || sending) return

    const idx = messages.findIndex((m) => m.id === msg.id)
    if (idx === -1) return
    const currentTail = messages.slice(idx + 1)
    const baseVersions: MessageVersion[] = msg.versions ?? [{ text: msg.text, tail: currentTail, pendingTurnId }]

    setEditingId(null)
    setError(null)
    setSending(true)
    try {
      let result: { messages: ChatMessage[]; pendingTurnId: string | null }
      if (msg.meta.kind === 'narrative') {
        result = await narrativeFlow(newText)
        result = { ...result, messages: [{ id: uid(), role: 'note', text: EDITED_NARRATIVE_NOTE }, ...result.messages] }
      } else {
        result = await answerFlow(msg.meta.turnId, newText)
      }

      const versions = [...baseVersions, { text: newText, tail: result.messages, pendingTurnId: result.pendingTurnId }]
      const updatedMsg: ChatMessage = { ...msg, text: newText, versions, activeVersion: versions.length - 1 }
      setPendingTurnId(result.pendingTurnId)
      setMessages((m) => [...m.slice(0, idx), updatedMsg, ...result.messages])
    } catch {
      setError('Could not resend the edited message. Check the backend and try again.')
    } finally {
      setSending(false)
    }
  }

  // Switches between versions of an edited message purely by swapping in the stored tail —
  // no backend call, since both versions' outcomes are already on record from when each was sent.
  function switchVersion(msg: ChatMessage, direction: 1 | -1) {
    if (!msg.versions || sending) return
    const idx = messages.findIndex((m) => m.id === msg.id)
    if (idx === -1) return
    const newIndex = (msg.activeVersion ?? 0) + direction
    if (newIndex < 0 || newIndex >= msg.versions.length) return
    const version = msg.versions[newIndex]
    setMessages((m) => [...m.slice(0, idx), { ...msg, text: version.text, activeVersion: newIndex }, ...version.tail])
    setPendingTurnId(version.pendingTurnId)
  }

  const lastUserIndex = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') return i
    }
    return -1
  })()

  return (
    <section
      style={{
        background: 'linear-gradient(180deg, rgba(255,255,255,0.015), rgba(255,255,255,0))',
        backgroundColor: colors.surface,
        border: `1px solid ${colors.border}`,
        borderRadius: 14,
        marginTop: '1.25rem',
        boxShadow: '0 1px 0 rgba(255,255,255,0.02) inset, 0 8px 24px -16px rgba(0,0,0,0.5)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <div style={{ padding: '1.5rem 1.6rem 0' }}>
        <PanelHeader
          icon="💬"
          title="Talk to Legal Lens"
          subtitle="A conversation, not a form — describe your situation and answer follow-ups as they come."
        />
      </div>

      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          maxHeight: 460,
          minHeight: 260,
          padding: '1rem 1.6rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.65rem',
        }}
      >
        {messages.map((m, idx) => {
          if (m.role === 'note') {
            return (
              <div key={m.id} style={{ ...calloutStyle.warn, alignSelf: 'center', fontSize: '0.8rem', padding: '0.5rem 0.85rem' }}>
                {m.text}
              </div>
            )
          }
          const isUser = m.role === 'user'
          const isEditable = isUser && idx === lastUserIndex && !!m.meta
          const isEditing = editingId === m.id
          const versionCount = m.versions?.length ?? 0
          const activeVersion = (m.activeVersion ?? 0) + 1

          if (isEditing) {
            return (
              <div key={m.id} style={{ alignSelf: 'flex-end', maxWidth: '85%', width: '100%' }}>
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleEditSave(m)
                    } else if (e.key === 'Escape') {
                      cancelEdit()
                    }
                  }}
                  rows={2}
                  autoFocus
                  style={{ ...inputStyle, width: '100%', resize: 'vertical' }}
                />
                <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'flex-end', marginTop: '0.4rem' }}>
                  <button style={ghostButtonStyle} onClick={cancelEdit}>
                    Cancel
                  </button>
                  <button
                    style={{ ...buttonStyle, padding: '0.32rem 0.8rem', fontSize: '0.78rem', ...disabledStyle(!editText.trim()) }}
                    onClick={() => handleEditSave(m)}
                    disabled={!editText.trim()}
                  >
                    Save &amp; resend
                  </button>
                </div>
              </div>
            )
          }

          return (
            <div key={m.id} style={{ alignSelf: isUser ? 'flex-end' : 'flex-start', maxWidth: '78%' }}>
              <div
                style={{
                  background: isUser ? colors.goldSoft : colors.surface2,
                  border: `1px solid ${isUser ? colors.goldBorder : colors.borderSoft}`,
                  borderRadius: isUser ? '12px 12px 3px 12px' : '12px 12px 12px 3px',
                  padding: '0.6rem 0.85rem',
                  fontSize: '0.92rem',
                  lineHeight: 1.5,
                  color: colors.text,
                }}
              >
                {m.text}
              </div>
              {m.sub && (
                <p style={{ fontSize: '0.76rem', color: colors.textFaint, marginTop: '0.3rem', paddingLeft: '0.2rem' }}>{m.sub}</p>
              )}
              {(isEditable || versionCount > 1) && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    gap: '0.5rem',
                    marginTop: '0.3rem',
                    fontSize: '0.72rem',
                    color: colors.textFaint,
                  }}
                >
                  {versionCount > 1 && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                      <button
                        style={{ ...ghostButtonStyle, padding: '0.05rem 0.4rem', fontSize: '0.72rem' }}
                        onClick={() => switchVersion(m, -1)}
                        disabled={activeVersion <= 1 || sending}
                      >
                        ‹
                      </button>
                      <span style={{ fontFamily: 'monospace' }}>
                        {activeVersion}/{versionCount}
                      </span>
                      <button
                        style={{ ...ghostButtonStyle, padding: '0.05rem 0.4rem', fontSize: '0.72rem' }}
                        onClick={() => switchVersion(m, 1)}
                        disabled={activeVersion >= versionCount || sending}
                      >
                        ›
                      </button>
                    </span>
                  )}
                  {isEditable && (
                    <button style={{ ...ghostButtonStyle, padding: '0.05rem 0.5rem', fontSize: '0.72rem' }} onClick={() => startEdit(m)} disabled={sending}>
                      Edit
                    </button>
                  )}
                </div>
              )}
            </div>
          )
        })}
        {sending && (
          <div style={{ alignSelf: 'flex-start' }}>
            <div
              style={{
                background: colors.surface2,
                border: `1px solid ${colors.borderSoft}`,
                borderRadius: '12px 12px 12px 3px',
                padding: '0.6rem 0.85rem',
                fontSize: '0.92rem',
                color: colors.textFaint,
              }}
            >
              …
            </div>
          </div>
        )}
      </div>

      {error && (
        <div style={{ padding: '0 1.6rem' }}>
          <div style={{ ...calloutStyle.danger, marginBottom: '0.75rem' }}>{error}</div>
        </div>
      )}

      <div
        style={{
          display: 'flex',
          gap: '0.6rem',
          padding: '1rem 1.6rem',
          borderTop: `1px solid ${colors.border}`,
          background: colors.bg,
        }}
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={hydrating ? 'Loading conversation…' : 'Type a message…'}
          rows={1}
          disabled={hydrating || !!editingId}
          style={{ ...inputStyle, flex: 1, resize: 'none', width: 'auto' }}
        />
        <button
          style={{ ...buttonStyle, ...disabledStyle(sending || hydrating || !!editingId || !input.trim()) }}
          onClick={handleSend}
          disabled={sending || hydrating || !!editingId || !input.trim()}
        >
          Send
        </button>
      </div>
    </section>
  )
}
