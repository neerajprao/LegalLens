import enum

from sqlalchemy.orm import Session

from app.agents.fact_extraction import FactExtractionAgent
from app.agents.law_retrieval import LawRetrievalAgent
from app.agents.legal_classification import LegalClassificationAgent
from app.models import Case, Event, Statement, StatementClassification


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
        return result

    def classify_and_retrieve(self, case: Case) -> dict:
        """Runs Legal Classification (hypotheses only, no citations) followed
        by Law Retrieval (real ChromaDB lookups, never fabricated) against
        the case's persisted statements and events. Hypotheses are not yet
        persisted to a dedicated table — no such entity exists in the Case
        Builder schema yet (CLAUDE.md §10.2 doesn't name one); this returns
        them directly rather than inventing a table ad hoc."""
        statements = [{"raw_text": s.raw_text, "classification": s.classification.value} for s in case.statements]
        events = [{"description": e.description, "occurred_at": e.occurred_at} for e in case.events]

        classification = self.legal_classification_agent.run({"statements": statements, "events": events})
        retrieval = self.law_retrieval_agent.run({"hypotheses": classification.get("hypotheses", [])})

        return {"classification": classification, "retrieval": retrieval}
