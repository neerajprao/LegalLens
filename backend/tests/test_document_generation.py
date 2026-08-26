import json

from fastapi.testclient import TestClient

from app.agents.document_generation import DocumentGenerationAgent
from app.main import app

client = TestClient(app)


def _fake_call_model(self, system, user_content, max_tokens=2048):
    return json.dumps({"content": "Case summary body.", "insufficient_case_state": False})


def test_generate_document_is_persisted(monkeypatch):
    monkeypatch.setattr(DocumentGenerationAgent, "_call_model", _fake_call_model)

    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/claims", json={"description": "Some claim"})

    response = client.post(f"/cases/{case_id}/documents", json={"draft_type": "case_summary"})
    assert response.status_code == 200
    body = response.json()

    assert body["content"] == "Case summary body."
    assert body["draft_type"] == "case_summary"
    assert body["draft_id"]


def test_generate_document_rejects_invalid_draft_type():
    case_id = client.post("/cases").json()["id"]
    response = client.post(f"/cases/{case_id}/documents", json={"draft_type": "not_a_real_type"})
    assert response.status_code == 200
    assert "error" in response.json()


def test_generate_document_on_empty_case_does_not_call_model(monkeypatch):
    def _fail_if_called(self, system, user_content, max_tokens=2048):
        raise AssertionError("should not call the model for an empty case state")

    monkeypatch.setattr(DocumentGenerationAgent, "_call_model", _fail_if_called)

    case_id = client.post("/cases").json()["id"]
    response = client.post(f"/cases/{case_id}/documents", json={"draft_type": "case_summary"})

    assert response.status_code == 200
    assert response.json()["insufficient_case_state"] is True
