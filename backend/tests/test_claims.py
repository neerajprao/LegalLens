import json

from fastapi.testclient import TestClient

from app.agents.claim_synthesis import ClaimSynthesisAgent
from app.agents.fact_extraction import FactExtractionAgent
from app.main import app

client = TestClient(app)


def _fake_fact_extraction(self, system, user_content, max_tokens=2048):
    return json.dumps(
        {
            "entities": ["Ramesh"],
            "events": [{"description": "threatened to hurt", "occurred_at": "2026-03-03", "is_approximate_date": False}],
            "statements": [{"raw_text": "Ramesh threatened to hurt me.", "classification": "fact"}],
        }
    )


def _fake_claim_synthesis(self, system, user_content, max_tokens=2048):
    return json.dumps({"claims": ["Ramesh threatened to hurt me on 3 March 2026."]})


def _fake_claim_synthesis_empty(self, system, user_content, max_tokens=2048):
    return json.dumps({"claims": []})


def _seed_case_with_facts(monkeypatch) -> str:
    monkeypatch.setattr(FactExtractionAgent, "_call_model", _fake_fact_extraction)
    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/narrative", json={"narrative": "placeholder narrative"})
    return case_id


def test_list_claims_empty_for_new_case():
    case_id = client.post("/cases").json()["id"]
    response = client.get(f"/cases/{case_id}/claims")
    assert response.status_code == 200
    assert response.json()["claims"] == []


def test_create_then_list_claim():
    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/claims", json={"description": "Manually added claim"})
    response = client.get(f"/cases/{case_id}/claims")
    claims = response.json()["claims"]
    assert len(claims) == 1
    assert claims[0]["description"] == "Manually added claim"
    assert claims[0]["status"] == "unsupported"


def test_update_claim_description():
    case_id = client.post("/cases").json()["id"]
    claim = client.post(f"/cases/{case_id}/claims", json={"description": "Original text"}).json()
    response = client.patch(f"/cases/{case_id}/claims/{claim['id']}", json={"description": "Edited text"})
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Edited text"

    listed = client.get(f"/cases/{case_id}/claims").json()["claims"]
    assert listed[0]["description"] == "Edited text"


def test_update_unknown_claim_returns_error():
    case_id = client.post("/cases").json()["id"]
    response = client.patch(f"/cases/{case_id}/claims/does-not-exist", json={"description": "x"})
    assert response.status_code == 200
    assert "error" in response.json()


def test_delete_claim_removes_it():
    case_id = client.post("/cases").json()["id"]
    claim = client.post(f"/cases/{case_id}/claims", json={"description": "To be deleted"}).json()
    response = client.delete(f"/cases/{case_id}/claims/{claim['id']}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True

    listed = client.get(f"/cases/{case_id}/claims").json()["claims"]
    assert listed == []


def test_suggest_claims_creates_grounded_claims(monkeypatch):
    case_id = _seed_case_with_facts(monkeypatch)
    monkeypatch.setattr(ClaimSynthesisAgent, "_call_model", _fake_claim_synthesis)

    response = client.post(f"/cases/{case_id}/claims/suggest")
    assert response.status_code == 200
    created = response.json()["claims"]
    assert len(created) == 1
    assert created[0]["description"] == "Ramesh threatened to hurt me on 3 March 2026."

    listed = client.get(f"/cases/{case_id}/claims").json()["claims"]
    assert len(listed) == 1


def test_suggest_claims_does_not_duplicate_on_second_call(monkeypatch):
    case_id = _seed_case_with_facts(monkeypatch)
    monkeypatch.setattr(ClaimSynthesisAgent, "_call_model", _fake_claim_synthesis)
    client.post(f"/cases/{case_id}/claims/suggest")

    second = client.post(f"/cases/{case_id}/claims/suggest")
    assert second.json()["claims"] == []

    listed = client.get(f"/cases/{case_id}/claims").json()["claims"]
    assert len(listed) == 1


def test_suggest_claims_on_empty_case_creates_nothing(monkeypatch):
    case_id = client.post("/cases").json()["id"]
    monkeypatch.setattr(ClaimSynthesisAgent, "_call_model", _fake_claim_synthesis_empty)

    response = client.post(f"/cases/{case_id}/claims/suggest")
    assert response.status_code == 200
    assert response.json()["claims"] == []
