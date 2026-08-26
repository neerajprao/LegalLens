import json

from fastapi.testclient import TestClient

from app.agents.fact_extraction import FactExtractionAgent
from app.main import app

client = TestClient(app)


def _fake_fact_extraction(self, system, user_content, max_tokens=2048):
    return json.dumps(
        {
            "entities": [],
            "events": [
                {"description": "Threat received", "occurred_at": "2026-03-15", "is_approximate_date": False},
                {"description": "First contact", "occurred_at": "2026-01-01", "is_approximate_date": False},
                {"description": "Something vague happened", "occurred_at": "sometime last year", "is_approximate_date": True},
            ],
            "statements": [],
        }
    )


def test_timeline_sorts_dated_events_and_separates_undated(monkeypatch):
    monkeypatch.setattr(FactExtractionAgent, "_call_model", _fake_fact_extraction)

    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/narrative", json={"narrative": "placeholder"})

    response = client.get(f"/cases/{case_id}/timeline")
    assert response.status_code == 200
    body = response.json()

    dated = body["dated_events"]
    assert [e["description"] for e in dated] == ["First contact", "Threat received"]
    assert len(body["undated_events"]) == 1
    assert body["undated_events"][0]["description"] == "Something vague happened"


def test_timeline_on_empty_case():
    case_id = client.post("/cases").json()["id"]
    response = client.get(f"/cases/{case_id}/timeline")
    assert response.status_code == 200
    body = response.json()
    assert body["dated_events"] == []
    assert body["undated_events"] == []
