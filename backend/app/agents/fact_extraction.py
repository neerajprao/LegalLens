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
- Extract specific, granular details whenever they are present — exact dates and times, names,
  amounts, locations, document/section references. Do not generalize away specifics that are
  actually in the text.
- If the input contains no identifiable case-relevant content — a greeting, small talk, or text
  too vague to extract anything from — return empty lists for entities, events, and statements.
  Do not invent or infer content just to have something to return.
- Output strict JSON only, matching this shape:
  {"entities": [...], "events": [{"description": str, "occurred_at": str, "is_approximate_date": bool}],
   "statements": [{"raw_text": str, "classification": str}]}
"""


class FactExtractionAgent(Agent):
    name = "fact_extraction"

    def run(self, case_state: dict[str, Any]) -> dict[str, Any]:
        """Uses the shared retry-once-on-malformed-JSON helper (base.py) —
        previously a single json.loads with no recovery, so one malformed
        response silently discarded an otherwise-usable model turn."""
        narrative = case_state.get("narrative", "")
        parsed, raw = self._call_model_json(system=SYSTEM_PROMPT, user_content=narrative)
        if parsed is None:
            return {"entities": [], "events": [], "statements": [], "parse_error": raw}
        return parsed
