import enum
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.agents.devils_advocate import DevilsAdvocateAgent
from app.agents.document_generation import DocumentGenerationAgent
from app.agents.dynamic_interview import DynamicInterviewAgent
from app.agents.evidence_gap_analysis import EvidenceGapAnalysisAgent
from app.agents.fact_extraction import FactExtractionAgent
from app.agents.law_retrieval import LawRetrievalAgent
from app.agents.legal_classification import LegalClassificationAgent
from app.agents.legal_strategy import LegalStrategyAgent
from app.agents.question_preparation import QuestionPreparationAgent
from app.config import settings
from app.evidence_extraction import extract_text_and_confidence
from app.models import (
    AuditLogEntry,
    Case,
    Claim,
    ClaimStatus,
    DocumentDraft,
    Event,
    Evidence,
    InterviewTurn,
    Statement,
    StatementClassification,
)

INTERVIEW_QUESTION_BUDGET = 10
"""Hard cap on questions per interview session (CLAUDE.md §9.2's OPEN
QUESTION on whole-interview stopping criterion, resolved 2026-08-24 as a
hybrid: this fixed budget as a hard ceiling, the agent's own per-turn
"sufficient" signal as a soft stop, and the caller can always end early via
end_interview() regardless of either)."""


class CaseStage(str, enum.Enum):
    """Hand-coded state machine driving the interview/case-building process
    (CLAUDE.md §8.1). Each stage maps to which agent(s) the orchestrator
    invokes next; conflict resolution between agent outputs happens here,
    not inside any individual agent."""

    intake = "intake"
    fact_extraction = "fact_extraction"
    legal_classification = "legal_classification"
    law_retrieval = "law_retrieval"
    evidence_gap_analysis = "evidence_gap_analysis"
    complete = "complete"


class Orchestrator:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.fact_extraction_agent = FactExtractionAgent()
        self.legal_classification_agent = LegalClassificationAgent()
        self.law_retrieval_agent = LawRetrievalAgent()
        self.evidence_gap_analysis_agent = EvidenceGapAnalysisAgent()
        self.devils_advocate_agent = DevilsAdvocateAgent()
        self.legal_strategy_agent = LegalStrategyAgent()
        self.document_generation_agent = DocumentGenerationAgent()
        self.dynamic_interview_agent = DynamicInterviewAgent()
        self.question_preparation_agent = QuestionPreparationAgent()

    def _log(self, case: Case, event_type: str, summary: str, payload: dict | None = None) -> None:
        """Appends one AuditLogEntry. Called after every material Case
        Builder mutation — see AuditLogEntry's docstring for why this one
        mechanism covers both §7's audit-logging requirement and §10.2's
        versioning question. Commits immediately so a log entry is never
        lost to a later rollback of an unrelated change in the same
        request."""
        self.db.add(
            AuditLogEntry(case_id=case.id, event_type=event_type, summary=summary, payload=json.dumps(payload or {}))
        )
        self.db.commit()

    # CLAUDE.md §9.4: a deliberately crude heuristic, not a geocoder or NER model — city/state
    # names strongly associated with a non-Karnataka jurisdiction. False positives (e.g. a
    # Bengaluru case mentioning a Mumbai-based bank branch in passing) are expected and
    # acceptable, because this only ever produces a non-binding warning, never an automatic
    # jurisdiction change.
    _OTHER_JURISDICTION_KEYWORDS = {
        "mumbai", "maharashtra", "delhi", "new delhi", "chennai", "tamil nadu", "hyderabad",
        "telangana", "kolkata", "west bengal", "pune", "ahmedabad", "gujarat", "jaipur",
        "rajasthan", "lucknow", "uttar pradesh", "patna", "bihar", "bhopal", "madhya pradesh",
        "kerala", "kochi", "punjab", "chandigarh", "goa",
    }

    def _detect_jurisdiction_mismatch(self, case: Case, narrative: str) -> str | None:
        text = narrative.lower()
        case_jurisdiction = case.jurisdiction.lower()
        hits = [kw for kw in self._OTHER_JURISDICTION_KEYWORDS if kw in text and kw not in case_jurisdiction]
        if not hits:
            return None
        return (
            f"Narrative mentions a location associated with a different jurisdiction ({', '.join(sorted(hits))}), "
            f"but this case is set to '{case.jurisdiction}'. This is a keyword heuristic, not a determination — "
            "review whether the case jurisdiction needs to be corrected, especially for cross-jurisdiction facts."
        )

    def submit_narrative(self, case: Case, narrative: str) -> dict:
        """Runs the fact-extraction step of the state machine for a case's
        initial narrative and persists the results. Evidence Gap Analysis is
        not wired up yet — this is the first working slice, not the full
        pipeline."""
        result = self.fact_extraction_agent.run({"narrative": narrative})

        for event in result.get("events", []):
            self.db.add(
                Event(
                    case_id=case.id,
                    description=event.get("description", ""),
                    occurred_at=event.get("occurred_at", ""),
                    is_approximate_date=event.get("is_approximate_date", False),
                    source="user_statement",
                )
            )

        for statement in result.get("statements", []):
            classification = statement.get("classification", "unknown")
            if classification not in StatementClassification.__members__:
                classification = "unknown"
            self.db.add(
                Statement(
                    case_id=case.id,
                    raw_text=statement.get("raw_text", ""),
                    classification=StatementClassification(classification),
                )
            )

        self.db.commit()
        self._log(
            case,
            "narrative_submitted",
            f"Narrative processed: {len(result.get('statements', []))} statements, {len(result.get('events', []))} events extracted.",
            {"narrative": narrative, "fact_extraction_result": result},
        )

        jurisdiction_warning = self._detect_jurisdiction_mismatch(case, narrative)
        if jurisdiction_warning:
            self._log(case, "jurisdiction_mismatch_flagged", jurisdiction_warning, {"case_jurisdiction": case.jurisdiction})
            result["jurisdiction_warning"] = jurisdiction_warning

        return result

    def classify_and_retrieve(self, case: Case) -> dict:
        """Runs Legal Classification (hypotheses only, no citations) followed
        by Law Retrieval (real ChromaDB lookups, never fabricated) against
        the case's persisted statements and events. Hypotheses are not yet
        persisted to a dedicated table — no such entity exists in the Case
        Builder schema yet (CLAUDE.md §10.2 doesn't name one); this returns
        them directly rather than inventing a table ad hoc.

        Skips the Legal Classification call entirely when the case has no
        facts yet — same short-circuit pattern used elsewhere (Devil's
        Advocate, Document Generation, Dynamic Interview), applied here at
        the shared source so every caller (Legal Strategy, Document
        Generation, Case Strength) benefits without repeating the check."""
        statements, events = self._facts_payload(case)

        if not statements and not events:
            classification = {"hypotheses": [], "insufficient_facts": True}
        else:
            classification = self.legal_classification_agent.run({"statements": statements, "events": events})
        retrieval = self.law_retrieval_agent.run({"hypotheses": classification.get("hypotheses", [])})

        return {"classification": classification, "retrieval": retrieval}

    def _compute_claim_statuses(self, case: Case) -> dict[str, ClaimStatus]:
        """Deterministically computes each claim's evidence-support status
        from the Case Builder's actual linked Evidence rows (CLAUDE.md
        §11.2's fact/evidence distinction enforced here, not by an LLM), and
        persists it onto the Claim rows. Shared by evidence_gap_analysis and
        devils_advocate so both see the same status without recomputing it
        differently. Only "unsupported" vs "supported" (>=1 linked evidence)
        is computed — "partially_supported"/"disputed" need sub-claim and
        evidence-disputation modeling this schema doesn't have yet."""
        status_by_claim: dict[str, ClaimStatus] = {}
        for claim in case.claims:
            linked = [e for e in case.evidence_items if e.linked_claim_id == claim.id]
            status = ClaimStatus.supported if linked else ClaimStatus.unsupported
            status_by_claim[claim.id] = status
            claim.status = status
        self.db.commit()
        return status_by_claim

    def evidence_gap_analysis(self, case: Case) -> dict:
        """Computes per-claim evidence-support status deterministically, then
        asks the agent only for the domain-informed "what evidence type
        would typically help" suggestion per claim (§11.3) — never for the
        support status itself."""
        status_by_claim = self._compute_claim_statuses(case)
        claim_payloads = [{"claim_id": c.id, "description": c.description} for c in case.claims]

        suggestions = self.evidence_gap_analysis_agent.run({"claims": claim_payloads})
        suggestions_by_claim = {s["claim_id"]: s["suggested_evidence_types"] for s in suggestions.get("suggestions", [])}

        gap_list = []
        for claim in case.claims:
            linked_evidence = [e for e in case.evidence_items if e.linked_claim_id == claim.id]
            low_confidence_evidence = [
                e.id for e in linked_evidence if e.extraction_confidence in ("low", "none")
            ]
            gap_list.append(
                {
                    "claim_id": claim.id,
                    "claim_description": claim.description,
                    "evidence_status": status_by_claim[claim.id].value,
                    "linked_evidence_count": len(linked_evidence),
                    "suggested_evidence_types": suggestions_by_claim.get(claim.id, []),
                    # CLAUDE.md §11.3: a claim can show "supported" from linked-evidence-count alone
                    # while the evidence's extracted text is actually unreliable — this field makes
                    # that visible instead of letting a low-confidence OCR result look as solid as a
                    # clean PDF extraction.
                    "low_confidence_evidence_ids": low_confidence_evidence,
                }
            )

        return {"gaps": gap_list}

    def devils_advocate(self, case: Case) -> dict:
        """Runs the Devil's Advocate agent against the case's persisted
        statements, events, and claims (CLAUDE.md §8.6) — the same fact base
        every other agent sees, nothing invented for it to attack. Claim
        evidence status is (re)computed the same deterministic way as
        evidence_gap_analysis, so "unsupported" claims are correctly flagged
        as the agent's raw material for missing-evidence vulnerabilities."""
        status_by_claim = self._compute_claim_statuses(case)
        statements, events = self._facts_payload(case)
        claim_payloads = [
            {"claim_id": c.id, "description": c.description, "evidence_status": status_by_claim[c.id].value}
            for c in case.claims
        ]

        return self.devils_advocate_agent.run({"statements": statements, "events": events, "claims": claim_payloads})

    def _facts_payload(self, case: Case) -> tuple[list[dict], list[dict]]:
        statements = [{"raw_text": s.raw_text, "classification": s.classification.value} for s in case.statements]
        events = [{"description": e.description, "occurred_at": e.occurred_at} for e in case.events]
        return statements, events

    @staticmethod
    def _flatten_retrieved_provisions(retrieval_result: dict) -> list[dict]:
        """Flattens LawRetrievalAgent's {category: [hits]} shape into a flat
        list of {chunk_id, act_name, section_number, text} for agents that
        just need "what was actually retrieved," not which hypothesis it
        came from. chunk_id (the ChromaDB document id) is what makes
        citation-binding (CLAUDE.md §12.6) possible: it's the one thing a
        generated citation can be checked against programmatically, rather
        than trusting the model's free-text self-report of what it cited."""
        flat: list[dict] = []
        for hits in retrieval_result.get("retrieved", {}).values():
            for hit in hits:
                meta = hit.get("metadata", {})
                flat.append(
                    {
                        "chunk_id": hit.get("chunk_id", ""),
                        "act_name": meta.get("act_name", ""),
                        "section_number": meta.get("section_number", ""),
                        "text": hit.get("text", ""),
                    }
                )
        return flat

    @staticmethod
    def _bind_citations(options: list[dict], retrieved_provisions: list[dict]) -> tuple[list[dict], list[str]]:
        """CLAUDE.md §12.6's citation-binding requirement, enforced in code:
        an agent's self-reported "citations" are checked against the actual
        retrieved chunk_ids, not trusted at face value. Any citation that
        doesn't correspond to a real retrieved chunk is stripped from the
        option (never shown to the user as if verified) and reported
        separately as dropped, so the gap is visible rather than silently
        hidden. A citation counts as valid only if it names a chunk_id that
        was actually retrieved for this case."""
        valid_ids = {p["chunk_id"] for p in retrieved_provisions if p.get("chunk_id")}
        dropped: list[str] = []
        bound_options = []
        for option in options:
            citations = option.get("citations", [])
            valid = [c for c in citations if c in valid_ids]
            invalid = [c for c in citations if c not in valid_ids]
            dropped.extend(invalid)
            bound_options.append({**option, "citations": valid})
        return bound_options, dropped

    def legal_strategy(self, case: Case, acknowledged: bool) -> dict:
        """CLAUDE.md §8.5: this agent ranks and recommends, so it carries
        meaningfully more product-boundary exposure than a pure options-list
        (§5). The doc's own DECISION REQUIRED recommended gating ranked
        recommendations behind explicit user acknowledgment but left it
        unconfirmed — resolved here as yes, gated, matching that
        recommendation: nothing from this agent is shown until the caller
        explicitly acknowledges the non-advice disclaimer."""
        if not acknowledged:
            return {
                "gated": True,
                "disclaimer": (
                    "Legal Strategy suggestions are not legal advice. They rank options based only "
                    "on facts and provisions currently in this case, and a court or lawyer would need "
                    "to determine the actual best course of action."
                ),
            }

        status_by_claim = self._compute_claim_statuses(case)
        statements, events = self._facts_payload(case)
        claim_payloads = [
            {"claim_id": c.id, "description": c.description, "evidence_status": status_by_claim[c.id].value}
            for c in case.claims
        ]

        classify_result = self.classify_and_retrieve(case)
        hypotheses = classify_result["classification"].get("hypotheses", [])
        retrieved_provisions = self._flatten_retrieved_provisions(classify_result["retrieval"])

        result = self.legal_strategy_agent.run(
            {
                "statements": statements,
                "events": events,
                "claims": claim_payloads,
                "hypotheses": hypotheses,
                "retrieved_provisions": retrieved_provisions,
            }
        )

        bound_options, dropped_citations = self._bind_citations(result.get("options", []), retrieved_provisions)
        result["options"] = bound_options
        if dropped_citations:
            result["unverified_citations_dropped"] = dropped_citations

        return {"gated": False, **result}

    def generate_document(self, case: Case, draft_type: str) -> dict:
        """CLAUDE.md §8.7: generates one draft, persisted as a DocumentDraft
        row. review_status defaults to "ai_draft" (unchanged schema default)
        but is no longer surfaced as a required visible watermark — that
        labeling requirement was removed 2026-08-24 at the user's explicit
        instruction (see §8.7's DECISION note)."""
        statements, events = self._facts_payload(case)
        status_by_claim = self._compute_claim_statuses(case)
        claim_payloads = [
            {"claim_id": c.id, "description": c.description, "evidence_status": status_by_claim[c.id].value}
            for c in case.claims
        ]

        retrieved_provisions: list[dict] = []
        if draft_type in ("complaint", "legal_notice"):
            classify_result = self.classify_and_retrieve(case)
            retrieved_provisions = self._flatten_retrieved_provisions(classify_result["retrieval"])

        result = self.document_generation_agent.run(
            {
                "draft_type": draft_type,
                "statements": statements,
                "events": events,
                "claims": claim_payloads,
                "retrieved_provisions": retrieved_provisions,
            }
        )

        draft = DocumentDraft(case_id=case.id, draft_type=draft_type, content=result.get("content", ""))
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)

        self._log(
            case,
            "document_generated",
            f"Generated {draft_type} draft (id={draft.id}).",
            {
                "draft_id": draft.id,
                "draft_type": draft_type,
                "case_state_used": {"statements": statements, "events": events, "claims": claim_payloads, "retrieved_provisions": retrieved_provisions},
            },
        )

        return {
            "draft_id": draft.id,
            "draft_type": draft.draft_type.value,
            "content": draft.content,
            "review_status": draft.review_status,
            "insufficient_case_state": result.get("insufficient_case_state", False),
        }

    def next_interview_question(self, case: Case) -> dict:
        """CLAUDE.md §9.2's question-selection loop. Hard budget check first
        (no agent call once INTERVIEW_QUESTION_BUDGET is reached — cheaper
        and deterministic, not left to the model to self-regulate). Prior
        turns are passed in so the agent can avoid re-asking already-covered
        material, per §9.2 step 4."""
        asked_count = len(case.interview_turns)
        if asked_count >= INTERVIEW_QUESTION_BUDGET:
            return {
                "next_question": None,
                "turn_id": None,
                "sufficient": True,
                "sufficiency_reason": f"question budget of {INTERVIEW_QUESTION_BUDGET} reached",
            }

        statements, events = self._facts_payload(case)
        prior_turns = [{"ref": t.id, "question": t.question, "answer": t.answer} for t in case.interview_turns]

        # No facts yet: skip Legal Classification entirely (nothing to classify) and let
        # DynamicInterviewAgent's own opening-narrative shortcut handle it without an LLM call.
        hypotheses: list[dict] = []
        if statements or events:
            classification = self.legal_classification_agent.run({"statements": statements, "events": events})
            hypotheses = classification.get("hypotheses", [])

        result = self.dynamic_interview_agent.run(
            {
                "operation": "next_question",
                "statements": statements,
                "events": events,
                "hypotheses": hypotheses,
                "prior_turns": prior_turns,
            }
        )

        next_question = result.get("next_question")
        if not next_question or result.get("sufficient"):
            return {
                "next_question": None,
                "turn_id": None,
                "sufficient": True,
                "sufficiency_reason": result.get("sufficiency_reason", ""),
            }

        turn = InterviewTurn(case_id=case.id, question=next_question, rationale=result.get("rationale", ""))
        self.db.add(turn)
        self.db.commit()
        self.db.refresh(turn)

        return {
            "next_question": turn.question,
            "turn_id": turn.id,
            "rationale": turn.rationale,
            "sufficient": False,
            "sufficiency_reason": "",
        }

    def submit_interview_answer(self, case: Case, turn_id: str, answer: str) -> dict:
        """Persists the answer (§7's audit-logging requirement), records it
        as a Statement so it feeds the Case Builder like any other fact
        (§9.1) — tagged "unknown" rather than run through a second Fact
        Extraction call per answer, a deliberate scope tradeoff, not an
        oversight — and runs contradiction detection against everything
        already known (§9.3). A contradiction never silently overwrites
        anything; both the new Statement and the flagged InterviewTurn stay
        in the Case Builder, visible to Devil's Advocate."""
        turn = next((t for t in case.interview_turns if t.id == turn_id), None)
        if turn is None:
            return {"error": "interview turn not found"}

        turn.answer = answer
        turn.answered_at = datetime.now(UTC)
        self.db.commit()

        statement = Statement(
            case_id=case.id,
            raw_text=answer,
            classification=StatementClassification.unknown,
            interview_turn_ref=turn.id,
        )
        self.db.add(statement)
        self.db.commit()

        prior_items = [{"ref": s.id, "text": s.raw_text} for s in case.statements if s.id != statement.id]
        prior_items += [
            {"ref": t.id, "text": t.answer} for t in case.interview_turns if t.answer and t.id != turn.id
        ]

        contradiction = self.dynamic_interview_agent.run(
            {"operation": "check_contradiction", "prior_items": prior_items, "new_answer": answer}
        )

        if contradiction.get("contradiction_found"):
            turn.contradicts_ref = contradiction.get("contradicts_ref")
            turn.contradiction_explanation = contradiction.get("explanation", "")
            self.db.commit()

        self._log(
            case,
            "interview_answer_submitted",
            f"Answered '{turn.question}': {answer}",
            {"turn_id": turn.id, "question": turn.question, "answer": answer, "contradiction": contradiction},
        )

        return {
            "turn_id": turn.id,
            "statement_id": statement.id,
            "contradiction_found": contradiction.get("contradiction_found", False),
            "contradicts_ref": turn.contradicts_ref,
            "contradiction_explanation": turn.contradiction_explanation,
        }

    def add_claim(self, case: Case, description: str) -> dict:
        claim = Claim(case_id=case.id, description=description)
        self.db.add(claim)
        self.db.commit()
        self.db.refresh(claim)
        self._log(case, "claim_added", f"Claim added: {description}", {"claim_id": claim.id, "description": description})
        return {"id": claim.id, "description": claim.description, "status": claim.status.value}

    def add_evidence(self, case: Case, evidence_type: str, description: str, linked_claim_id: str | None) -> dict:
        evidence = Evidence(
            case_id=case.id, evidence_type=evidence_type, description=description, linked_claim_id=linked_claim_id
        )
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        self._log(
            case,
            "evidence_added",
            f"Evidence added: {evidence_type} ({description})",
            {"evidence_id": evidence.id, "evidence_type": evidence_type, "linked_claim_id": linked_claim_id},
        )
        return {"id": evidence.id, "evidence_type": evidence.evidence_type, "linked_claim_id": evidence.linked_claim_id}

    def add_evidence_with_file(
        self, case: Case, evidence_type: str, description: str, linked_claim_id: str | None, filename: str, file_bytes: bytes
    ) -> dict:
        """CLAUDE.md §11.3: saves the uploaded file, extracts text (PDF text
        layer or image OCR — see evidence_extraction.py for exact scope),
        and stores an explicit confidence indicator alongside it. Low
        confidence is stored, not hidden or upgraded — callers of this
        Evidence row (currently none downstream yet; extracted_text isn't
        consumed by any agent) must check extraction_confidence before
        treating extracted_text as reliable, per §11.3's requirement."""
        evidence_dir = Path(settings.evidence_store_dir)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4()}_{filename}"
        file_path = evidence_dir / stored_name
        file_path.write_bytes(file_bytes)

        extracted_text, confidence = extract_text_and_confidence(file_path)

        evidence = Evidence(
            case_id=case.id,
            evidence_type=evidence_type,
            description=description,
            linked_claim_id=linked_claim_id,
            file_path=str(file_path),
            extracted_text=extracted_text,
            extraction_confidence=confidence,
        )
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        self._log(
            case,
            "evidence_uploaded",
            f"Evidence file uploaded: {filename} ({evidence_type}), extraction confidence: {confidence}",
            {"evidence_id": evidence.id, "filename": filename, "extraction_confidence": confidence},
        )
        return {
            "id": evidence.id,
            "evidence_type": evidence.evidence_type,
            "linked_claim_id": evidence.linked_claim_id,
            "extracted_text": evidence.extracted_text,
            "extraction_confidence": evidence.extraction_confidence,
        }

    def audit_log(self, case: Case) -> dict:
        """CLAUDE.md §7: retrieves the full append-only history for a case —
        the reconstruction mechanism for §10.2's versioning question. Each
        entry's payload carries enough of the relevant case-state slice to
        answer "what did the system know when this happened," though full
        state at time T means replaying entries up to T, not one lookup
        (see AuditLogEntry's docstring for that limitation)."""
        return {
            "entries": [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "summary": e.summary,
                    "payload": json.loads(e.payload),
                    "created_at": e.created_at.isoformat(),
                }
                for e in case.audit_log
            ]
        }

    @staticmethod
    def _aggregate_band(supported_count: int, total_claims: int, unresolved_contradictions: int, hypothesis_count: int) -> str:
        """CLAUDE.md §15.2's OPEN QUESTION resolved 2026-08-24: yes, include ONE coarse
        categorical band alongside the fully disaggregated detail, never instead of it. This is
        NOT a probability or win-likelihood — §15.1's rejection of naive scoring is absolute and
        this doesn't touch it. It's a purely deterministic function of already-computed counts
        (no LLM involved, so it can't be talked into a rosier answer), meant only as a rough
        completeness signal a user can act on ("what should I do next"), not a verdict."""
        if total_claims == 0:
            return "early-stage"
        support_ratio = supported_count / total_claims
        if support_ratio >= 0.7 and unresolved_contradictions == 0 and hypothesis_count <= 1:
            return "well-documented"
        if support_ratio >= 0.3 or total_claims > 0:
            return "partially-documented"
        return "early-stage"

    def case_strength(self, case: Case) -> dict:
        """CLAUDE.md §15: synthesizes outputs already produced by other agents
        into the multi-dimensional, qualitative-first presentation §15.2
        specifies — this method makes no LLM call of its own beyond what
        classify_and_retrieve and devils_advocate already make; it never
        computes or presents a single aggregate score (§15.1's firm
        constraint), only the coarse band decided above alongside full detail."""
        status_by_claim = self._compute_claim_statuses(case)
        evidence_coverage = [
            {"claim_id": c.id, "description": c.description, "evidence_status": status_by_claim[c.id].value}
            for c in case.claims
        ]

        disputed_facts = [
            {
                "turn_id": t.id,
                "question": t.question,
                "answer": t.answer,
                "contradicts_ref": t.contradicts_ref,
                "explanation": t.contradiction_explanation,
            }
            for t in case.interview_turns
            if t.contradicts_ref
        ]

        classify_result = self.classify_and_retrieve(case)
        hypotheses = classify_result["classification"].get("hypotheses", [])
        legal_uncertainty = []
        if len(hypotheses) > 1:
            legal_uncertainty.append(
                {
                    "description": "Multiple plausible legal classifications, not yet resolved.",
                    "hypotheses": [h.get("category") for h in hypotheses],
                }
            )
        elif len(hypotheses) == 0 and (case.statements or case.events):
            legal_uncertainty.append(
                {"description": "No legal classification hypothesis could be formed yet from known facts.", "hypotheses": []}
            )

        devils_result = self.devils_advocate(case)
        counterarguments = [
            {
                "description": w.get("description", ""),
                "related_claim_id": w.get("related_claim_id"),
                "severity": w.get("severity", "unspecified"),
            }
            for w in devils_result.get("weaknesses", [])
        ]

        supported_count = sum(1 for s in status_by_claim.values() if s == ClaimStatus.supported)
        band = self._aggregate_band(
            supported_count=supported_count,
            total_claims=len(case.claims),
            unresolved_contradictions=len(disputed_facts),
            hypothesis_count=len(hypotheses),
        )

        flagged_conflicts = self._flag_agent_conflicts(hypotheses, counterarguments)

        return {
            "evidence_coverage": evidence_coverage,
            "disputed_facts": disputed_facts,
            "legal_uncertainty": legal_uncertainty,
            "counterarguments": counterarguments,
            "opposing_arguments": devils_result.get("opposing_arguments", []),
            "flagged_conflicts": flagged_conflicts,
            "aggregate_band": band,
            "aggregate_band_disclaimer": (
                "This is a rough documentation-completeness signal, not a probability of success "
                "or a legal verdict. It is computed only from counts already shown in the sections "
                "above and can be misleading if the case is small or unusual — read the detail, not "
                "just this label."
            ),
        }

    @staticmethod
    def _flag_agent_conflicts(hypotheses: list[dict], counterarguments: list[dict]) -> list[dict]:
        """CLAUDE.md §8.1/§8.8's inter-agent conflict-resolution rule,
        resolved 2026-08-24: the orchestrator's policy is SURFACE, not
        silently resolve. No agent has authority over another — when Legal
        Classification proposes hypotheses and Devil's Advocate separately
        raises a "strong" weakness, that tension is shown explicitly rather
        than one agent's output being presented as if uncontested (§8.1's
        own worked example: "Legal Classification suggests category A,
        Devil's Advocate flags contradiction"). This is deliberately a
        simple juxtaposition rule, not a reconciliation algorithm — there is
        no basis for the orchestrator to decide which agent is "more
        right"."""
        if not hypotheses:
            return []
        strong_weaknesses = [c for c in counterarguments if c.get("severity") == "strong"]
        if not strong_weaknesses:
            return []
        return [
            {
                "description": (
                    "Legal Classification proposed one or more categories while Devil's Advocate "
                    "separately identified a strong weakness in the case. Neither is treated as "
                    "authoritative over the other — both are shown so this can be weighed directly."
                ),
                "hypotheses": [h.get("category") for h in hypotheses],
                "strong_weaknesses": [w.get("description") for w in strong_weaknesses],
            }
        ]

    @staticmethod
    def _try_parse_date(raw: str) -> datetime | None:
        """Best-effort parse of occurred_at free text. Never guesses past
        what's actually parseable — an unparseable date stays unparseable
        and is surfaced as such (see timeline()), not silently dropped or
        coerced to a wrong-looking date."""
        if not raw:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y", "%d %B %Y", "%B %Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw.strip(), fmt)
            except ValueError:
                continue
        return None

    def timeline(self, case: Case) -> dict:
        """CLAUDE.md §10.2's Timeline entity: an orderable sequence of
        Events with explicit handling of uncertain/approximate dates. Not a
        separate stored entity — computed from Event rows already
        persisted, since ordering is a read-time concern, not something
        that needs its own write path. Events with an unparseable
        occurred_at are surfaced in a separate "undated" list rather than
        silently sorted to the start/end or dropped."""
        dated = []
        undated = []
        for event in case.events:
            parsed = self._try_parse_date(event.occurred_at)
            entry = {
                "id": event.id,
                "description": event.description,
                "occurred_at": event.occurred_at,
                "is_approximate_date": event.is_approximate_date,
                "source": event.source,
            }
            if parsed is not None:
                dated.append((parsed, entry))
            else:
                undated.append(entry)

        dated.sort(key=lambda pair: pair[0])
        return {"dated_events": [entry for _, entry in dated], "undated_events": undated}

    def prepare_questions(self, case: Case) -> dict:
        """CLAUDE.md §14: generates questions the person might face plus
        suggested responses, strictly grounded in known facts. Audience
        resolved 2026-08-24 as plain-language-by-default (see the agent's
        own docstring). Reuses the same deterministic evidence-status
        computation as every other claim-aware agent so claims are
        described consistently."""
        status_by_claim = self._compute_claim_statuses(case)
        statements, events = self._facts_payload(case)
        claim_payloads = [
            {"claim_id": c.id, "description": c.description, "evidence_status": status_by_claim[c.id].value}
            for c in case.claims
        ]

        return self.question_preparation_agent.run({"statements": statements, "events": events, "claims": claim_payloads})
