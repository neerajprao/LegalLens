import json

from fastapi.testclient import TestClient

from app.agents.devils_advocate import DevilsAdvocateAgent
from app.main import app

client = TestClient(app)


def _fake_call_model(self, system, user_content, max_tokens=2048):
    payload = json.loads(user_content)
    unsupported = [c for c in payload["claims"] if c["evidence_status"] == "unsupported"]
    return json.dumps(
        {
            "weaknesses": [
                {"description": f"No evidence linked to: {c['description']}", "related_claim_id": c["claim_id"]}
                for c in unsupported
            ],
            "opposing_arguments": ["The other side could argue the events happened differently."],
            "alternative_interpretations": ["The same facts could be read as a civil dispute, not a criminal one."],
            "insufficient_case_state": False,
        }
    )


def test_devils_advocate_flags_unsupported_claim(monkeypatch):
    monkeypatch.setattr(DevilsAdvocateAgent, "_call_model", _fake_call_model)

    case_id = client.post("/cases").json()["id"]
    claim = client.post(f"/cases/{case_id}/claims", json={"description": "Assault occurred on a specific date"}).json()

    response = client.post(f"/cases/{case_id}/devils-advocate")
    assert response.status_code == 200
    body = response.json()

    assert body["insufficient_case_state"] is False
    weaknesses = body["weaknesses"]
    assert any(w["related_claim_id"] == claim["id"] for w in weaknesses)


def test_devils_advocate_on_empty_case_does_not_call_model(monkeypatch):
    def _fail_if_called(self, system, user_content, max_tokens=2048):
        raise AssertionError("should not call the model for an empty case state")

    monkeypatch.setattr(DevilsAdvocateAgent, "_call_model", _fail_if_called)

    case_id = client.post("/cases").json()["id"]
    response = client.post(f"/cases/{case_id}/devils-advocate")

    assert response.status_code == 200
    assert response.json()["insufficient_case_state"] is True
