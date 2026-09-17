import json

from fastapi.testclient import TestClient

from app.agents.document_generation import DocumentGenerationAgent
from app.agents.law_retrieval import LawRetrievalAgent
from app.agents.legal_classification import LegalClassificationAgent
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


def test_generate_document_drops_unverified_citation(monkeypatch):
    """CLAUDE.md §12.6 citation-binding, extended to Document Generation: a
    self-reported citations_used entry that doesn't match a real retrieved
    chunk_id is reported as unverified/dropped rather than trusted."""

    def _fake_classification(self, system, user_content, max_tokens=2048):
        return json.dumps({"hypotheses": [{"category": "criminal intimidation", "rationale": "test", "confidence": "medium"}]})

    def _fake_retrieval(self, case_state):
        return {
            "retrieved": {
                "criminal intimidation": [
                    {"chunk_id": "BNS_2023-350", "text": "Criminal intimidation text.", "metadata": {"act_name": "BNS_2023", "section_number": "351"}}
                ]
            },
            "insufficient_data": False,
            "note": "",
        }

    def _fake_generation(self, system, user_content, max_tokens=2048):
        return json.dumps(
            {
                "content": "Complaint citing BNS S351 and a fabricated section.",
                "citations_used": ["BNS_2023-350", "FABRICATED_CHUNK_ID"],
                "insufficient_case_state": False,
            }
        )

    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification)
    monkeypatch.setattr(LawRetrievalAgent, "run", _fake_retrieval)
    monkeypatch.setattr(DocumentGenerationAgent, "_call_model", _fake_generation)

    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/claims", json={"description": "Threatening messages were sent"})

    response = client.post(f"/cases/{case_id}/documents", json={"draft_type": "complaint"})
    assert response.status_code == 200
    body = response.json()

    assert body["verified_citations"] == ["BNS_2023-350"]
    assert body["unverified_citations_dropped"] == ["FABRICATED_CHUNK_ID"]
    assert "citation_warning" in body
