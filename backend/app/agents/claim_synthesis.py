import json
from typing import Any

from app.agents.base import Agent

SYSTEM_PROMPT = """You are the Claim Synthesis agent in Legal Lens, operating on the criminal-law
domain for Karnataka, India.

You are given the statements and events already known about a case (from the narrative and
interview so far). Identify the distinct claims or allegations the user appears to be asserting,
each as a single clear sentence in plain language.

Rules:
- Every claim must be grounded strictly in the given statements/events — never invent a claim,
  person, or detail that isn't actually present in the input.
- Consolidate closely related statements into one claim rather than listing every sentence
  separately (e.g., "Ramesh threatened me on March 3rd, and I have a recording of it" is one
  claim, not two).
- Skip incidental details that aren't themselves an assertion of wrongdoing or a disputed fact —
  a bare date or location on its own is not a claim.
- If nothing in the input rises to the level of an assertable claim, return an empty list rather
  than forcing one.
- Phrase each claim the way the user would say it, not in legal jargon.

Output strict JSON only, matching this shape:
  {"claims": [str, ...]}
"""


class ClaimSynthesisAgent(Agent):
    name = "claim_synthesis"

    def run(self, case_state: dict[str, Any]) -> dict[str, Any]:
        statements = case_state.get("statements", [])
        events = case_state.get("events", [])
        if not statements and not events:
            return {"claims": []}

        user_content = json.dumps({"statements": statements, "events": events})
        parsed, raw = self._call_model_json(system=SYSTEM_PROMPT, user_content=user_content)
        if parsed is None:
            return {"claims": [], "parse_error": raw}
        return parsed
