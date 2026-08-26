import json

from fastapi.testclient import TestClient

from app.agents.devils_advocate import DevilsAdvocateAgent
from app.agents.fact_extraction import FactExtractionAgent
from app.agents.law_retrieval import LawRetrievalAgent
from app.agents.legal_classification import LegalClassificationAgent
from app.main import app

client = TestClient(app)

FORBIDDEN_KEYS = {"probability", "win_probability", "score", "confidence_score", "likelihood"}


def _fake_fact_extraction(self, system, user_content, max_tokens=2048):
    return json.dumps(
        {
            "entities": [],
            "events": [{"description": "An altercation occurred", "occurred_at": "2026-01-01", "is_approximate_date": False}],
            "statements": [{"raw_text": "The altercation occurred on 1 January 2026.", "classification": "fact"}],
        }
    )


def _fake_classification_single(self, system, user_content, max_tokens=2048):
    return json.dumps({"hypotheses": [{"category": "criminal intimidation", "rationale": "test", "confidence": "medium"}]})


def _fake_classification_multi(self, system, user_content, max_tokens=2048):
    return json.dumps(
        {
            "hypotheses": [
                {"category": "criminal intimidation", "rationale": "test", "confidence": "medium"},
                {"category": "assault", "rationale": "test", "confidence": "low"},
            ]
        }
    )


def _fake_devils_advocate(self, system, user_content, max_tokens=2048):
    payload = json.loads(user_content)
    unsupported = [c for c in payload["claims"] if c["evidence_status"] == "unsupported"]
    return json.dumps(
        {
            "weaknesses": [
                {"description": f"No evidence for: {c['description']}", "related_claim_id": c["claim_id"], "severity": "strong"}
                for c in unsupported
            ],
            "opposing_arguments": ["Opposing side could argue timeline is unclear."],
            "alternative_interpretations": [],
            "insufficient_case_state": False,
        }
    )


def _no_retrieval(self, case_state):
    return {"retrieved": {}, "insufficient_data": True, "note": ""}


def test_case_strength_never_returns_a_numeric_score(monkeypatch):
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification_single)
    monkeypatch.setattr(LawRetrievalAgent, "run", _no_retrieval)
    monkeypatch.setattr(DevilsAdvocateAgent, "_call_model", _fake_devils_advocate)

    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/claims", json={"description": "Threatening messages were sent"})

    response = client.get(f"/cases/{case_id}/strength")
    assert response.status_code == 200
    body = response.json()

    def _walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert k.lower() not in FORBIDDEN_KEYS, f"found forbidden scoring key: {k}"
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(body)
    assert body["aggregate_band"] in {"early-stage", "partially-documented", "well-documented"}
    assert "aggregate_band_disclaimer" in body


def test_case_strength_evidence_coverage_and_counterarguments(monkeypatch):
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification_single)
    monkeypatch.setattr(LawRetrievalAgent, "run", _no_retrieval)
    monkeypatch.setattr(DevilsAdvocateAgent, "_call_model", _fake_devils_advocate)

    case_id = client.post("/cases").json()["id"]
    supported = client.post(f"/cases/{case_id}/claims", json={"description": "Threatening messages were sent"}).json()
    unsupported = client.post(f"/cases/{case_id}/claims", json={"description": "Assault occurred"}).json()
    client.post(
        f"/cases/{case_id}/evidence",
        json={"evidence_type": "messages", "description": "Screenshots", "linked_claim_id": supported["id"]},
    )

    response = client.get(f"/cases/{case_id}/strength")
    body = response.json()

    coverage = {c["claim_id"]: c["evidence_status"] for c in body["evidence_coverage"]}
    assert coverage[supported["id"]] == "supported"
    assert coverage[unsupported["id"]] == "unsupported"

    weaknesses = body["counterarguments"]
    assert any(w["related_claim_id"] == unsupported["id"] and w["severity"] == "strong" for w in weaknesses)


def test_case_strength_flags_multiple_classifications_as_uncertainty(monkeypatch):
    monkeypatch.setattr(FactExtractionAgent, "_call_model", _fake_fact_extraction)
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification_multi)
    monkeypatch.setattr(LawRetrievalAgent, "run", _no_retrieval)
    monkeypatch.setattr(DevilsAdvocateAgent, "_call_model", _fake_devils_advocate)

    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/narrative", json={"narrative": "placeholder"})
    client.post(f"/cases/{case_id}/claims", json={"description": "Something happened"})

    response = client.get(f"/cases/{case_id}/strength")
    body = response.json()

    assert len(body["legal_uncertainty"]) == 1
    assert set(body["legal_uncertainty"][0]["hypotheses"]) == {"criminal intimidation", "assault"}


def test_case_strength_on_empty_case():
    case_id = client.post("/cases").json()["id"]
    response = client.get(f"/cases/{case_id}/strength")
    assert response.status_code == 200
    body = response.json()
    assert body["evidence_coverage"] == []
    assert body["aggregate_band"] == "early-stage"


def test_case_strength_flags_conflict_between_classification_and_strong_weakness(monkeypatch):
    monkeypatch.setattr(FactExtractionAgent, "_call_model", _fake_fact_extraction)
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification_single)
    monkeypatch.setattr(LawRetrievalAgent, "run", _no_retrieval)
    monkeypatch.setattr(DevilsAdvocateAgent, "_call_model", _fake_devils_advocate)

    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/narrative", json={"narrative": "placeholder"})
    client.post(f"/cases/{case_id}/claims", json={"description": "Assault occurred"})  # left unsupported -> "strong" weakness

    response = client.get(f"/cases/{case_id}/strength")
    body = response.json()

    assert len(body["flagged_conflicts"]) == 1
    conflict = body["flagged_conflicts"][0]
    assert conflict["hypotheses"] == ["criminal intimidation"]
    assert len(conflict["strong_weaknesses"]) == 1


def test_case_strength_no_conflict_when_no_strong_weaknesses(monkeypatch):
    monkeypatch.setattr(FactExtractionAgent, "_call_model", _fake_fact_extraction)
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification_single)
    monkeypatch.setattr(LawRetrievalAgent, "run", _no_retrieval)
    monkeypatch.setattr(DevilsAdvocateAgent, "_call_model", _fake_devils_advocate)

    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/narrative", json={"narrative": "placeholder"})
    claim = client.post(f"/cases/{case_id}/claims", json={"description": "Threats were made"}).json()
    client.post(
        f"/cases/{case_id}/evidence",
        json={"evidence_type": "messages", "description": "Screenshots", "linked_claim_id": claim["id"]},
    )  # supported -> no "strong" weakness generated for it

    response = client.get(f"/cases/{case_id}/strength")
    body = response.json()

    assert body["flagged_conflicts"] == []
