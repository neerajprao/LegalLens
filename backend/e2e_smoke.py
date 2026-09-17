"""One-off live end-to-end smoke run (CLAUDE.md Phase 6/9): drives the real
FastAPI app in-process against the REAL dev database, REAL ChromaDB corpus,
and a REAL local LLM (Ollama + Qwen3.5 9B) -- nothing mocked. Not a pytest
test (pytest's conftest.py deliberately overrides get_db to an isolated
in-memory DB for test isolation; this script intentionally does NOT import
conftest, so it hits the real backend/data/db/legal_lens.db and
data/vector_store/).

Prints each stage's real output so it can be read and judged, not just
asserted pass/fail. Meant to be run once, by hand, then the dev DB reset
afterward -- not part of the CI test suite.

HISTORICAL NOTE: an earlier run of this script (2026-08-26, against
Gemini's free tier before the switch to fully-local) completed 10 of 13
stages before hitting Gemini's daily free-tier quota (20 requests/day).
That constraint doesn't apply to the local model -- no rate limit, no
quota, no cost -- but each real call now takes roughly 10-20 seconds on
Apple M3 Pro / 18GB, so a full run takes several minutes, not several
seconds. Requires the Ollama app/daemon running locally with
`qwen3.5:9b-q4_K_M` (or whatever OLLAMA_MODEL is set to) already pulled.
"""

import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def show(label: str, obj) -> None:
    print(f"\n--- {label} ---")
    print(json.dumps(obj, indent=2, default=str)[:4000])


# 1. Create case
section("1. CREATE CASE")
case = client.post("/cases").json()
case_id = case["id"]
show("case", case)

# 2. Submit narrative
section("2. SUBMIT NARRATIVE -> Fact Extraction")
narrative = (
    "On the evening of 3 January 2026, my neighbor Ravi Kumar sent me a series of WhatsApp "
    "messages threatening to harm me and my family after a dispute over the boundary wall "
    "between our properties. He said he would 'make sure I regret it' if I didn't tear down "
    "the wall I had built. I have screenshots of these messages saved on my phone. I did not "
    "report this to the police immediately because I was afraid of retaliation, but I told my "
    "sister about it the same night."
)
narrative_result = client.post(f"/cases/{case_id}/narrative", json={"narrative": narrative}).json()
show("fact_extraction result", narrative_result)

# 3. Interview: get next question, answer it, check contradiction detection
section("3. DYNAMIC INTERVIEW")
question = client.post(f"/cases/{case_id}/interview/next-question").json()
show("next question", question)

if question.get("turn_id"):
    # Deliberately contradicts "I did not report this to the police immediately"
    answer_result = client.post(
        f"/cases/{case_id}/interview/answer",
        json={"turn_id": question["turn_id"], "answer": "I actually called the police right away that same evening."},
    ).json()
    show("answer result (testing contradiction detection)", answer_result)

# 4. Timeline
section("4. TIMELINE")
timeline = client.get(f"/cases/{case_id}/timeline").json()
show("timeline", timeline)

# 5. Add a claim + evidence
section("5. CLAIMS & EVIDENCE")
claim = client.post(f"/cases/{case_id}/claims", json={"description": "Ravi Kumar sent threatening WhatsApp messages"}).json()
show("claim", claim)
evidence = client.post(
    f"/cases/{case_id}/evidence",
    json={"evidence_type": "messages", "description": "Screenshots of WhatsApp threats", "linked_claim_id": claim["id"]},
).json()
show("evidence", evidence)

unsupported_claim = client.post(f"/cases/{case_id}/claims", json={"description": "Ravi Kumar has a history of harassment"}).json()
show("second (unsupported) claim", unsupported_claim)

# 6. Classification + real Law Retrieval
section("6. LEGAL CLASSIFICATION + LAW RETRIEVAL (real ChromaDB query)")
classify_result = client.post(f"/cases/{case_id}/classify").json()
show("classification + retrieval", classify_result)

# 7. Evidence gap analysis
section("7. EVIDENCE GAP ANALYSIS")
gaps = client.post(f"/cases/{case_id}/evidence-gaps").json()
show("evidence gaps", gaps)

# 8. Devil's Advocate
section("8. DEVIL'S ADVOCATE")
devils = client.post(f"/cases/{case_id}/devils-advocate").json()
show("devils advocate", devils)

# 9. Legal Strategy (gated, then acknowledged)
section("9. LEGAL STRATEGY")
gated = client.post(f"/cases/{case_id}/strategy", json={"acknowledged": False}).json()
show("strategy (gated)", gated)
strategy = client.post(f"/cases/{case_id}/strategy", json={"acknowledged": True}).json()
show("strategy (acknowledged)", strategy)

# 10. Question preparation
section("10. QUESTION PREPARATION")
questions = client.post(f"/cases/{case_id}/questions").json()
show("prepared questions", questions)

# 11. Document generation (complaint -- pulls in retrieved provisions + citation binding)
section("11. DOCUMENT GENERATION (complaint)")
complaint = client.post(f"/cases/{case_id}/documents", json={"draft_type": "complaint"}).json()
show("complaint draft", complaint)

# 12. Case strength
section("12. CASE STRENGTH")
strength = client.get(f"/cases/{case_id}/strength").json()
show("case strength", strength)

# 13. Audit log
section("13. AUDIT LOG")
audit = client.get(f"/cases/{case_id}/audit-log").json()
print(f"\n{len(audit['entries'])} audit log entries:")
for e in audit["entries"]:
    print(f"  [{e['event_type']}] {e['summary'][:100]}")

section("DONE")
print(f"case_id = {case_id}")
