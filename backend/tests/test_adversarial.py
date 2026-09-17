"""Phase 6: hallucination / adversarial testing (CLAUDE.md §7, §15.1, §16,
§21). Two kinds of test here:

1. Tests that PROVE an existing guardrail actually holds under an
   adversarial input (not just a happy-path input) — these assert the
   system behaves safely.
2. A test that documents a known, real gap in current guardrail coverage
   — this asserts what the system does NOT catch, so the gap is tracked
   honestly (CLAUDE.md's own "safety over completeness" principle: say
   what's uncertain/unverified rather than silently pretending it's
   covered) rather than hidden by only testing the cases that pass.
"""

import json

from fastapi.testclient import TestClient

from app.agents.devils_advocate import DevilsAdvocateAgent
from app.agents.document_generation import DocumentGenerationAgent
from app.agents.dynamic_interview import DynamicInterviewAgent
from app.agents.fact_extraction import FactExtractionAgent
from app.agents.law_retrieval import LawRetrievalAgent
from app.agents.legal_classification import LegalClassificationAgent
from app.main import app

client = TestClient(app)


def _fake_fact_extraction(self, system, user_content, max_tokens=2048):
    return json.dumps(
        {
            "entities": [],
            "events": [{"description": "An altercation occurred", "occurred_at": "2026-01-01", "is_approximate_date": False}],
            "statements": [{"raw_text": "The altercation occurred.", "classification": "fact"}],
        }
    )


def _fake_classification_single(self, system, user_content, max_tokens=2048):
    return json.dumps({"hypotheses": [{"category": "criminal intimidation", "rationale": "test", "confidence": "high"}]})


def _real_retrieval_one_hit(self, case_state):
    return {
        "retrieved": {
            "criminal intimidation": [
                {"chunk_id": "BNS_2023-350", "text": "Real retrieved text.", "metadata": {"act_name": "BNS_2023", "section_number": "351"}}
            ]
        },
        "insufficient_data": False,
        "note": "",
    }


def test_known_gap_fabricated_section_embedded_in_prose_is_not_caught(monkeypatch):
    """Documents a real, still-open limitation (CLAUDE.md §12.7's OPEN
    QUESTION on exact verification mechanism) rather than hiding it:
    citation *binding* (Orchestrator._bind_citations, tested in
    test_document_generation.py) only checks the self-reported
    `citations_used` LIST against real retrieved chunk_ids. It does
    nothing to a fabricated section number an agent embeds directly in
    the drafted prose text itself, outside that list — that text is
    returned to the user completely unchecked. This test intentionally
    asserts the fabricated text SURVIVES untouched — proving the gap
    exists, not that it's fixed — so it's tracked as a known limitation,
    not silently assumed covered by the citations_used check."""

    def _fake_generation_with_fabricated_prose_citation(self, system, user_content, max_tokens=2048):
        return json.dumps(
            {
                # citations_used correctly lists only the real chunk_id...
                "content": "The complainant may rely on BNS Section 999 (a completely fabricated section) in addition to the retrieved provision.",
                "citations_used": ["BNS_2023-350"],
                "insufficient_case_state": False,
            }
        )

    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification_single)
    monkeypatch.setattr(LawRetrievalAgent, "run", _real_retrieval_one_hit)
    monkeypatch.setattr(DocumentGenerationAgent, "_call_model", _fake_generation_with_fabricated_prose_citation)

    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/claims", json={"description": "Threatening messages were sent"})

    response = client.post(f"/cases/{case_id}/documents", json={"draft_type": "complaint"})
    body = response.json()

    # The binding check passes cleanly (citations_used only names the real chunk)...
    assert body.get("unverified_citations_dropped") is None
    # ...yet the fabricated "BNS Section 999" reference is still sitting in the
    # returned content, completely unverified. This is the gap.
    assert "BNS Section 999" in body["content"]


def test_case_strength_band_is_not_well_documented_when_a_contradiction_is_unresolved(monkeypatch):
    """Adversarial test against overconfident presentation (CLAUDE.md
    §15.1's firm rejection of naive scoring, §15.2's aggregate-band
    design): even when every claim is fully evidence-supported and there's
    only one legal hypothesis — the two conditions that would otherwise
    earn "well-documented" — an unresolved contradiction must still hold
    the band back. Proves the band can't be pushed to look more solid than
    the case's actual documented state by an agent alone; the check is a
    pure function of counts including contradictions, not something an
    LLM's tone can talk it into."""

    def _fake_devils_advocate_no_weaknesses(self, system, user_content, max_tokens=2048):
        return json.dumps(
            {
                "weaknesses": [],
                "opposing_arguments": [],
                "alternative_interpretations": [],
                "insufficient_case_state": False,
            }
        )

    def _no_retrieval(self, case_state):
        return {"retrieved": {}, "insufficient_data": True, "note": ""}

    monkeypatch.setattr(FactExtractionAgent, "_call_model", _fake_fact_extraction)
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification_single)
    monkeypatch.setattr(LawRetrievalAgent, "run", _no_retrieval)
    monkeypatch.setattr(DevilsAdvocateAgent, "_call_model", _fake_devils_advocate_no_weaknesses)

    case_id = client.post("/cases").json()["id"]

    # Seed a prior Statement first -- submit_interview_answer's contradiction check
    # short-circuits (never calls the model) when there's nothing yet to contradict.
    client.post(f"/cases/{case_id}/narrative", json={"narrative": "placeholder narrative"})

    # Fully supported claim -> would otherwise satisfy "well-documented"'s support-ratio bar.
    claim = client.post(f"/cases/{case_id}/claims", json={"description": "Threatening messages were sent"}).json()
    client.post(
        f"/cases/{case_id}/evidence",
        json={"evidence_type": "messages", "description": "Screenshots", "linked_claim_id": claim["id"]},
    )

    # Force an unresolved contradiction through the real interview flow (not a direct DB
    # write) -- same API path a real user session would take.
    def _fake_next_question(self, system, user_content, max_tokens=2048):
        return json.dumps(
            {
                "next_question": "Did you report this immediately?",
                "rationale": "test",
                "sufficient": False,
                "sufficiency_reason": "",
            }
        )

    def _fake_contradiction_found(self, system, user_content, max_tokens=2048):
        return json.dumps(
            {
                "contradiction_found": True,
                "contradicts_ref": claim["id"],
                "explanation": "Contradicts an earlier statement that the user reported it the same day.",
            }
        )

    monkeypatch.setattr(DynamicInterviewAgent, "_call_model", _fake_next_question)
    question = client.post(f"/cases/{case_id}/interview/next-question").json()
    monkeypatch.setattr(DynamicInterviewAgent, "_call_model", _fake_contradiction_found)
    answer = client.post(
        f"/cases/{case_id}/interview/answer",
        json={"turn_id": question["turn_id"], "answer": "No, I never told anyone."},
    ).json()
    assert answer["contradiction_found"] is True

    response = client.get(f"/cases/{case_id}/strength")
    body = response.json()

    assert len(body["disputed_facts"]) == 1
    assert body["aggregate_band"] != "well-documented"
