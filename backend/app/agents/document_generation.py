import json
from typing import Any

from app.agents.base import Agent

SYSTEM_PROMPT = """You are the Complaint / Case Document Generation agent in Legal Lens,
operating on the criminal-law domain for Karnataka, India.

You are asked to draft one document of a specific type ("draft_type") from the case's verified
state: statements/events (facts), claims with evidence-support status, and any legal provisions
actually retrieved from the verified knowledge base (each with act name, section number, text).

Hard rules — these are non-negotiable:
- Do NOT invent facts, parties, dates, or events that are not present in the given case state.
  If a needed detail (e.g., a party's full name, an exact date) is missing, write a clear
  placeholder like "[DATE NOT YET PROVIDED]" rather than inventing one.
- Do NOT cite any act, section number, or legal provision that is not present in the given
  retrieved_provisions list. If none were retrieved, do not cite any statute at all — draft the
  document on the facts alone and note that applicable provisions have not yet been verified.
- Unsupported claims (evidence_status: "unsupported") must not be stated as established fact in
  the document — phrase them as the complainant's assertion, not as fact.

Output strict JSON only, matching this shape:
  {"content": str, "insufficient_case_state": bool}
"""

VALID_DRAFT_TYPES = {
    "complaint",
    "legal_notice",
    "case_summary",
    "chronology",
    "evidence_list",
    "statement",
    "question_set",
}


class DocumentGenerationAgent(Agent):
    name = "document_generation"

    def run(self, case_state: dict[str, Any]) -> dict[str, Any]:
        draft_type = case_state.get("draft_type")
        if draft_type not in VALID_DRAFT_TYPES:
            raise ValueError(f"unknown draft_type: {draft_type!r}")

        statements = case_state.get("statements", [])
        events = case_state.get("events", [])
        claims = case_state.get("claims", [])
        if not statements and not events and not claims:
            return {
                "content": "Insufficient case information to draft this document yet.",
                "insufficient_case_state": True,
            }

        user_content = json.dumps(
            {
                "draft_type": draft_type,
                "statements": statements,
                "events": events,
                "claims": claims,
                "retrieved_provisions": case_state.get("retrieved_provisions", []),
            }
        )
        raw = self._call_model(system=SYSTEM_PROMPT, user_content=user_content, max_tokens=4096)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "content": "Draft generation failed to produce valid output.",
                "insufficient_case_state": False,
                "parse_error": raw,
            }
