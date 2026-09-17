export const API_BASE = 'http://localhost:8000'

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`)
  return res.json()
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`)
  return res.json()
}

async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`)
  return res.json()
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`)
  return res.json()
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`)
  return res.json()
}

export type Statement = { raw_text: string; classification: string }
export type EventItem = { description: string; occurred_at: string; is_approximate_date: boolean }

export type FactExtractionResult = {
  entities?: unknown[]
  events?: EventItem[]
  statements?: Statement[]
  parse_error?: string
}

export type Claim = { id: string; description: string; status: string }
export type Evidence = { id: string; evidence_type: string; linked_claim_id: string | null }
export type EvidenceInventoryItem = {
  id: string
  evidence_type: string
  description: string
  linked_claim_id: string | null
  extraction_confidence: string
  disputed: boolean
  has_file: boolean
}
export type EvidenceInventoryResult = { evidence: EvidenceInventoryItem[] }

export type Hypothesis = { category: string; rationale: string; confidence: string }
export type ProvisionMetadata = {
  act_name: string
  section_number: string
  section_title: string
  source_file: string
  page_number: number
  jurisdiction: string
  effective_from: string
  effective_to: string
  repealed_by: string
  successor_of: string
}
export type ClassifyResult = {
  classification: { hypotheses: Hypothesis[]; insufficient_facts?: boolean }
  retrieval: {
    retrieved: Record<string, { text: string; metadata: ProvisionMetadata; distance: number }[]>
    insufficient_data: boolean
    note: string
  }
}

export type EvidenceGap = {
  claim_id: string
  claim_description: string
  evidence_status: string
  linked_evidence_count: number
  suggested_evidence_types: string[]
  low_confidence_evidence_ids: string[]
}
export type EvidenceGapsResult = { gaps: EvidenceGap[] }

export type EvidenceUploadResult = {
  id: string
  evidence_type: string
  linked_claim_id: string | null
  extracted_text: string
  extraction_confidence: 'high' | 'medium' | 'low' | 'none'
}

export type Weakness = { description: string; related_claim_id: string | null; severity?: string }
export type DevilsAdvocateResult = {
  weaknesses: Weakness[]
  opposing_arguments: string[]
  alternative_interpretations: string[]
  insufficient_case_state: boolean
}

export type StrategyOption = { description: string; rationale: string; citations: string[] }
export type StrategyResult = {
  gated: boolean
  disclaimer?: string
  options?: StrategyOption[]
  suggested_best_path?: { description: string; rationale: string } | null
  insufficient_case_state?: boolean
}

export type DraftType =
  | 'complaint'
  | 'legal_notice'
  | 'case_summary'
  | 'chronology'
  | 'evidence_list'
  | 'statement'
  | 'question_set'

export type DocumentResult = {
  draft_id: string
  draft_type: DraftType
  content: string
  review_status: string
  insufficient_case_state: boolean
  verified_citations?: string[]
  unverified_citations_dropped?: string[]
  citation_warning?: string
}

export type InterviewQuestionResult = {
  next_question: string | null
  turn_id: string | null
  rationale?: string
  sufficient: boolean
  sufficiency_reason: string
}

export type InterviewAnswerResult = {
  turn_id: string
  statement_id: string
  contradiction_found: boolean
  contradicts_ref: string | null
  contradicts_text: string | null
  contradiction_explanation: string
}

export type CaseStrengthResult = {
  evidence_coverage: { claim_id: string; description: string; evidence_status: string }[]
  disputed_facts: {
    turn_id: string
    question: string
    answer: string | null
    contradicts_ref: string | null
    contradicts_text: string | null
    explanation: string
  }[]
  legal_uncertainty: { description: string; hypotheses: string[] }[]
  counterarguments: Weakness[]
  opposing_arguments: string[]
  flagged_conflicts: { description: string; hypotheses: string[]; strong_weaknesses: string[] }[]
  aggregate_band: 'early-stage' | 'partially-documented' | 'well-documented'
  aggregate_band_disclaimer: string
}

export type TimelineEvent = { id: string; description: string; occurred_at: string; is_approximate_date: boolean; source: string }
export type TimelineResult = { dated_events: TimelineEvent[]; undated_events: TimelineEvent[] }

export type AuditLogEntry = { id: string; event_type: string; summary: string; payload: Record<string, unknown>; created_at: string }
export type AuditLogResult = { entries: AuditLogEntry[] }

export type PreparedQuestion = { question: string; source: string; suggested_response: string | null; gap_note: string }
export type QuestionPreparationResult = { questions: PreparedQuestion[]; insufficient_case_state: boolean }

export type CaseSummary = { id: string; status: string; jurisdiction: string; error?: string }
export type InterviewTurnRecord = {
  turn_id: string
  question: string
  rationale: string
  answer: string | null
  contradicts_ref: string | null
  contradicts_text: string | null
  contradiction_explanation: string
  created_at: string
  answered_at: string | null
}
export type InterviewTurnsResult = { turns: InterviewTurnRecord[] }

export const api = {
  createCase: () => post<{ id: string; status: string; jurisdiction: string }>('/cases'),
  getCase: (caseId: string) => get<CaseSummary>(`/cases/${caseId}`),
  interviewTurns: (caseId: string) => get<InterviewTurnsResult>(`/cases/${caseId}/interview/turns`),
  submitNarrative: (caseId: string, narrative: string) =>
    post<{ fact_extraction: FactExtractionResult }>(`/cases/${caseId}/narrative`, { narrative }),
  classify: (caseId: string) => post<ClassifyResult>(`/cases/${caseId}/classify`),
  listClaims: (caseId: string) => get<{ claims: Claim[] }>(`/cases/${caseId}/claims`),
  createClaim: (caseId: string, description: string) => post<Claim>(`/cases/${caseId}/claims`, { description }),
  suggestClaims: (caseId: string) => post<{ claims: Claim[] }>(`/cases/${caseId}/claims/suggest`),
  updateClaim: (caseId: string, claimId: string, description: string) =>
    patch<Claim>(`/cases/${caseId}/claims/${claimId}`, { description }),
  deleteClaim: (caseId: string, claimId: string) => del<{ id: string; deleted: boolean }>(`/cases/${caseId}/claims/${claimId}`),
  createEvidence: (caseId: string, evidence_type: string, description: string, linked_claim_id: string | null) =>
    post<Evidence>(`/cases/${caseId}/evidence`, { evidence_type, description, linked_claim_id }),
  uploadEvidence: (caseId: string, evidence_type: string, description: string, linked_claim_id: string | null, file: File) => {
    const form = new FormData()
    form.append('evidence_type', evidence_type)
    form.append('description', description)
    if (linked_claim_id) form.append('linked_claim_id', linked_claim_id)
    form.append('file', file)
    return postForm<EvidenceUploadResult>(`/cases/${caseId}/evidence/upload`, form)
  },
  evidenceGaps: (caseId: string) => post<EvidenceGapsResult>(`/cases/${caseId}/evidence-gaps`),
  listEvidence: (caseId: string) => get<EvidenceInventoryResult>(`/cases/${caseId}/evidence`),
  disputeEvidence: (caseId: string, evidenceId: string, disputed: boolean) =>
    patch<{ id: string; disputed: boolean }>(`/cases/${caseId}/evidence/${evidenceId}/dispute`, { disputed }),
  devilsAdvocate: (caseId: string) => post<DevilsAdvocateResult>(`/cases/${caseId}/devils-advocate`),
  strategy: (caseId: string, acknowledged: boolean) =>
    post<StrategyResult>(`/cases/${caseId}/strategy`, { acknowledged }),
  generateDocument: (caseId: string, draft_type: DraftType) =>
    post<DocumentResult>(`/cases/${caseId}/documents`, { draft_type }),
  nextInterviewQuestion: (caseId: string) => post<InterviewQuestionResult>(`/cases/${caseId}/interview/next-question`),
  submitInterviewAnswer: (caseId: string, turn_id: string, answer: string) =>
    post<InterviewAnswerResult>(`/cases/${caseId}/interview/answer`, { turn_id, answer }),
  caseStrength: (caseId: string) => get<CaseStrengthResult>(`/cases/${caseId}/strength`),
  timeline: (caseId: string) => get<TimelineResult>(`/cases/${caseId}/timeline`),
  auditLog: (caseId: string) => get<AuditLogResult>(`/cases/${caseId}/audit-log`),
  prepareQuestions: (caseId: string) => post<QuestionPreparationResult>(`/cases/${caseId}/questions`),
}
