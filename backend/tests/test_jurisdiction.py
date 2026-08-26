import json

from fastapi.testclient import TestClient

from app.agents.fact_extraction import FactExtractionAgent
from app.main import app

client = TestClient(app)


def _fake_fact_extraction(self, system, user_content, max_tokens=2048):
    return json.dumps({"entities": [], "events": [], "statements": []})


def test_create_case_with_explicit_jurisdiction():
    response = client.post("/cases", json={"jurisdiction": "India - Maharashtra"})
    assert response.status_code == 200
    assert response.json()["jurisdiction"] == "India - Maharashtra"


def test_create_case_without_jurisdiction_defaults_to_karnataka():
    response = client.post("/cases", json={})
    assert response.status_code == 200
    assert response.json()["jurisdiction"] == "India - Karnataka"


def test_narrative_flags_jurisdiction_mismatch(monkeypatch):
    monkeypatch.setattr(FactExtractionAgent, "_call_model", _fake_fact_extraction)

    case_id = client.post("/cases", json={}).json()["id"]
    response = client.post(
        f"/cases/{case_id}/narrative",
        json={"narrative": "The incident happened at a shop in Mumbai, Maharashtra."},
    )

    assert response.status_code == 200
    assert "jurisdiction_warning" in response.json()["fact_extraction"]


def test_narrative_no_warning_when_jurisdiction_matches(monkeypatch):
    monkeypatch.setattr(FactExtractionAgent, "_call_model", _fake_fact_extraction)

    case_id = client.post("/cases", json={}).json()["id"]
    response = client.post(
        f"/cases/{case_id}/narrative",
        json={"narrative": "The incident happened at a shop in Bengaluru, Karnataka."},
    )

    assert response.status_code == 200
    assert "jurisdiction_warning" not in response.json()["fact_extraction"]
