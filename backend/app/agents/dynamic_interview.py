import json
from typing import Any

from app.agents.base import Agent

NEXT_QUESTION_PROMPT = """You are the Dynamic Legal Interview agent in Legal Lens, operating on
the criminal-law domain for Karnataka, India.

You are given: statements/events already known about the case, the current legal-classification
hypotheses (candidate categories, not confirmed), and every interview question already asked
(with its answer, if answered).

Select the SINGLE next most legally material question to ask — the one whose answer would most
change or confirm the current hypothesis set (CLAUDE.md §9.2). Do not ask about anything already
covered by an existing statement or a previously-asked question, even rephrased.

Rules:
- Ask only what is legally material — no idle curiosity, no interrogation for its own sake.
- Plain language: the user may have no legal knowledge.
- One question at a time.
- Every question needs a one-sentence rationale explaining WHY this answer would matter (what
  hypothesis it would confirm/rule out, or what evidence gap it addresses).
- Signal "sufficient": true when you judge the marginal value of further questions on this
  case is now low relative to what's already known — this is one input the orchestrator uses to
  decide whether to keep going, not the only one.

Output strict JSON only, matching this shape:
  {"next_question": str | null, "rationale": str, "sufficient": bool, "sufficiency_reason": str}
If sufficient is true, next_question may be null.
"""

CONTRADICTION_CHECK_PROMPT = """You are checking a single new interview answer against
everything already known about a Legal Lens case (statements, events, and prior interview
answers) for the criminal-law domain, Karnataka, India.

Does the new answer contradict any specific prior statement or answer? A contradiction means
they cannot both be true as stated (e.g., conflicting dates, conflicting accounts of who did
what) — not merely that the new answer adds detail or nuance.

Rules:
- Only flag a genuine contradiction, not elaboration, correction of your own prior
  misunderstanding, or additional detail.
- If you flag one, identify exactly which prior item (by the "ref" given for it) conflicts, and
  explain the conflict in one sentence.
- Do not invent a contradiction that isn't actually there.

Output strict JSON only, matching this shape:
  {"contradiction_found": bool, "contradicts_ref": str | null, "explanation": str}
"""


class DynamicInterviewAgent(Agent):
    name = "dynamic_interview"

    def run(self, case_state: dict[str, Any]) -> dict[str, Any]:
        operation = case_state.get("operation")
        if operation == "next_question":
            return self._next_question(case_state)
        if operation == "check_contradiction":
            return self._check_contradiction(case_state)
        raise ValueError(f"unknown operation: {operation!r}")

    def _next_question(self, case_state: dict[str, Any]) -> dict[str, Any]:
        statements = case_state.get("statements", [])
        events = case_state.get("events", [])
        prior_turns = case_state.get("prior_turns", [])

        if not statements and not events:
            return {
                "next_question": "Can you describe what happened, in your own words?",
                "rationale": "No facts are known yet — an opening narrative is needed before any material question can be selected.",
                "sufficient": False,
                "sufficiency_reason": "",
            }

        user_content = json.dumps(
            {
                "statements": statements,
                "events": events,
                "hypotheses": case_state.get("hypotheses", []),
                "prior_turns": prior_turns,
            }
        )
        raw = self._call_model(system=NEXT_QUESTION_PROMPT, user_content=user_content)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"next_question": None, "rationale": "", "sufficient": False, "sufficiency_reason": "", "parse_error": raw}

    def _check_contradiction(self, case_state: dict[str, Any]) -> dict[str, Any]:
        prior_items = case_state.get("prior_items", [])
        new_answer = case_state.get("new_answer", "")
        if not prior_items or not new_answer:
            return {"contradiction_found": False, "contradicts_ref": None, "explanation": ""}

        user_content = json.dumps({"prior_items": prior_items, "new_answer": new_answer})
        raw = self._call_model(system=CONTRADICTION_CHECK_PROMPT, user_content=user_content)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"contradiction_found": False, "contradicts_ref": None, "explanation": "", "parse_error": raw}
