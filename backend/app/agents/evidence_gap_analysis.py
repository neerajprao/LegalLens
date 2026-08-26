import json
from typing import Any

from app.agents.base import Agent

SYSTEM_PROMPT = """You are the Evidence Gap Analysis agent in Legal Lens, operating on the
criminal-law domain for Karnataka, India.

You are given a list of claims/allegations, each already tagged with its evidence-support
status (computed separately — you do not decide this). For each claim, suggest the evidence
TYPES that would typically help support or test a claim of this kind (e.g., "witness statement",
"CCTV footage", "medical examination report", "call records", "FIR copy"). This is a
domain-informed heuristic about what evidence commonly matters for this kind of claim, not a
demand that the user produce it, and not a judgment on whether the claim is true.

Rules:
- Do not comment on whether the claim is true, likely, or well-founded — that is out of scope
  for this agent.
- Do not invent facts about the case; work only from the claim description given.
- Keep each suggestion list short (2-5 items), concrete, and specific to that claim.

Output strict JSON only, matching this shape:
  {"suggestions": [{"claim_id": str, "suggested_evidence_types": [str, ...]}]}
"""


class EvidenceGapAnalysisAgent(Agent):
    name = "evidence_gap_analysis"

    def run(self, case_state: dict[str, Any]) -> dict[str, Any]:
        claims = case_state.get("claims", [])
        if not claims:
            return {"suggestions": []}

        user_content = json.dumps({"claims": claims})
        raw = self._call_model(system=SYSTEM_PROMPT, user_content=user_content)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"suggestions": [], "parse_error": raw}
