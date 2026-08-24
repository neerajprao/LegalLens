import json
from typing import Any

from app.agents.base import Agent

SYSTEM_PROMPT = """You are the Fact Extraction agent in Legal Lens, a legal case-preparation assistant.

Given a user's narrative about a legal situation, extract:
- entities: people, organizations, locations, dates mentioned
- events: discrete things that happened, each with a description and approximate date if known
- statements: each distinct assertion in the narrative, tagged as exactly one of
  "fact", "assumption", "opinion", "allegation", or "unknown"

Rules:
- Do not merge distinct people or events into one.
- Do not tag opinion or allegation as fact.
- If a statement is ambiguous, tag it "unknown" rather than guessing or silently dropping it.
- Output strict JSON only, matching this shape:
  {"entities": [...], "events": [{"description": str, "occurred_at": str, "is_approximate_date": bool}],
   "statements": [{"raw_text": str, "classification": str}]}
"""


class FactExtractionAgent(Agent):
    name = "fact_extraction"

    def run(self, case_state: dict[str, Any]) -> dict[str, Any]:
        narrative = case_state.get("narrative", "")
        raw = self._call_model(system=SYSTEM_PROMPT, user_content=narrative)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"entities": [], "events": [], "statements": [], "parse_error": raw}
