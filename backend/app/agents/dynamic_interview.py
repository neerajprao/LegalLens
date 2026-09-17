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
- Never signal "sufficient": true while basic elements (who was involved, what happened, roughly
  when, roughly where) are still unknown, or while only one or two thin statements/events are on
  record. Sparse or vague input is a reason to ask a clarifying question, not a reason to stop.

Output strict JSON only, matching this shape:
  {"next_question": str | null, "rationale": str, "sufficient": bool, "sufficiency_reason": str}
If sufficient is true, next_question may be null.
"""

CONTRADICTION_CHECK_PROMPT = """You are checking a single new interview answer against
everything already known about a Legal Lens case (statements, events, and prior interview
answers) for the criminal-law domain, Karnataka, India.

Judge this the way a careful human reader would: read the new answer and each prior item for
what they actually mean as a whole, in context — never by matching individual words or phrases
against each other. Different wording, a paraphrase, a synonym, an approximation, or a more
specific version of the same underlying fact is NOT a contradiction. Only flag one when the two
items assert something that literally cannot both be true about the same specific fact (the same
date, the same actor, the same action, the same location) — a genuine factual conflict, not a
difference in phrasing.

NOT a contradiction (do not flag these):
- New answer adds detail the old one didn't mention ("near my house" then later "outside my
  house, at 12 MG Road" — the second is just more specific, not conflicting).
- New answer uses different words for the same thing ("voice recording" vs. "audio recording";
  "threatened" vs. "said he would hurt me").
- New answer gives an approximate time/date where the old one was vague or absent, or vice
  versa, as long as they're compatible ("that evening" then later "around 9pm that evening").
- New answer describes a different event, person, or topic entirely — nothing to compare, so
  nothing to contradict.

IS a contradiction (flag these):
- Two answers give incompatible specifics about the same fact ("it happened on Monday" vs. "it
  happened on Wednesday" — cannot both be true about one single event).
- Two answers name different people in the same role for the same event ("my neighbor Ramesh did
  it" vs. "my neighbor Suresh did it", referring to the same single incident).

Before deciding, first reason in one or two sentences about whether the new answer and any prior
item describe the SAME specific fact and actually conflict, or are merely differently worded /
more detailed / about something else. Only after that reasoning, decide.

Rules:
- Only flag a genuine, specific factual conflict — never a difference in wording alone.
- If you flag one, identify exactly which prior item (by the "ref" given for it) conflicts, and
  explain the conflict in one sentence, referencing the specific fact that conflicts.
- When genuinely unsure whether something is a real conflict or just a wording difference,
  do not flag it — a missed contradiction is far less harmful here than a false one.

Output strict JSON only, matching this shape:
  {"reasoning": str, "contradiction_found": bool, "contradicts_ref": str | null, "explanation": str}
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
        parsed, raw = self._call_model_json(system=NEXT_QUESTION_PROMPT, user_content=user_content)
        if parsed is None:
            return {"next_question": None, "rationale": "", "sufficient": False, "sufficiency_reason": "", "parse_error": raw}
        return parsed

    def _check_contradiction(self, case_state: dict[str, Any]) -> dict[str, Any]:
        prior_items = case_state.get("prior_items", [])
        new_answer = case_state.get("new_answer", "")
        if not prior_items or not new_answer:
            return {"contradiction_found": False, "contradicts_ref": None, "explanation": ""}

        user_content = json.dumps({"prior_items": prior_items, "new_answer": new_answer})
        parsed, raw = self._call_model_json(system=CONTRADICTION_CHECK_PROMPT, user_content=user_content)
        if parsed is None:
            return {"contradiction_found": False, "contradicts_ref": None, "explanation": "", "parse_error": raw}
        return parsed
