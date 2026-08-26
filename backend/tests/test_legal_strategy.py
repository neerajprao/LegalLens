import json

from fastapi.testclient import TestClient

from app.agents.law_retrieval import LawRetrievalAgent
from app.agents.legal_classification import LegalClassificationAgent
from app.agents.legal_strategy import LegalStrategyAgent
from app.main import app

client = TestClient(app)


def _fake_classification(self, system, user_content, max_tokens=2048):
    return json.dumps(
        {"hypotheses": [{"category": "criminal intimidation", "rationale": "test", "confidence": "medium"}]}
    )


def _fake_strategy(self, system, user_content, max_tokens=2048):
    return json.dumps(
        {
            "options": [{"description": "File a complaint", "rationale": "based on given facts", "citations": []}],
            "suggested_best_path": {"description": "File a complaint", "rationale": "based on given facts"},
            "insufficient_case_state": False,
        }
    )


def test_strategy_is_gated_without_acknowledgment(monkeypatch):
    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/claims", json={"description": "Some claim"})

    response = client.post(f"/cases/{case_id}/strategy", json={"acknowledged": False})
    assert response.status_code == 200
    body = response.json()

    assert body["gated"] is True
    assert "disclaimer" in body
    assert "options" not in body


def test_strategy_returns_options_when_acknowledged(monkeypatch):
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification)
    monkeypatch.setattr(LawRetrievalAgent, "run", lambda self, case_state: {"retrieved": {}, "insufficient_data": True, "note": ""})
    monkeypatch.setattr(LegalStrategyAgent, "_call_model", _fake_strategy)

    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/claims", json={"description": "Some claim"})

    response = client.post(f"/cases/{case_id}/strategy", json={"acknowledged": True})
    assert response.status_code == 200
    body = response.json()

    assert body["gated"] is False
    assert len(body["options"]) == 1
    assert body["suggested_best_path"]["description"] == "File a complaint"


def _fake_strategy_with_fabricated_citation(self, system, user_content, max_tokens=2048):
    payload = json.loads(user_content)
    real_chunk_id = payload["retrieved_provisions"][0]["chunk_id"]
    return json.dumps(
        {
            "options": [
                {
                    "description": "File a complaint under BNS §351",
                    "rationale": "supported by a real retrieved provision",
                    "citations": [real_chunk_id],
                },
                {
                    "description": "Send a legal notice citing a made-up section",
                    "rationale": "the model hallucinated this citation",
                    "citations": ["chunk-that-does-not-exist-12345"],
                },
            ],
            "suggested_best_path": None,
            "insufficient_case_state": False,
        }
    )


def _fake_retrieval_with_one_real_hit(self, case_state):
    return {
        "retrieved": {
            "criminal intimidation": [
                {
                    "chunk_id": "BNS_2023-42",
                    "text": "351. Criminal intimidation.—Whoever threatens another...",
                    "metadata": {"act_name": "BNS_2023", "section_number": "351"},
                    "distance": 0.1,
                }
            ]
        },
        "insufficient_data": False,
        "note": "",
    }


def test_strategy_strips_fabricated_citations_not_in_retrieved_provisions(monkeypatch):
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification)
    monkeypatch.setattr(LawRetrievalAgent, "run", _fake_retrieval_with_one_real_hit)
    monkeypatch.setattr(LegalStrategyAgent, "_call_model", _fake_strategy_with_fabricated_citation)

    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/claims", json={"description": "Some claim"})

    response = client.post(f"/cases/{case_id}/strategy", json={"acknowledged": True})
    assert response.status_code == 200
    body = response.json()

    real_option, fabricated_option = body["options"]
    assert real_option["citations"] == ["BNS_2023-42"]
    assert fabricated_option["citations"] == []
    assert "chunk-that-does-not-exist-12345" in body["unverified_citations_dropped"]
