import json

from fastapi.testclient import TestClient

from app.agents.dynamic_interview import DynamicInterviewAgent
from app.agents.fact_extraction import FactExtractionAgent
from app.agents.legal_classification import LegalClassificationAgent
from app.main import app
from app.orchestrator import INTERVIEW_QUESTION_BUDGET

client = TestClient(app)


def _fake_classification(self, system, user_content, max_tokens=2048):
    return json.dumps({"hypotheses": []})


def _fake_fact_extraction(self, system, user_content, max_tokens=2048):
    return json.dumps(
        {
            "entities": [],
            "events": [{"description": "An altercation occurred", "occurred_at": "2026-01-01", "is_approximate_date": False}],
            "statements": [{"raw_text": "The altercation occurred on 1 January 2026.", "classification": "fact"}],
        }
    )


def _fake_next_question(self, system, user_content, max_tokens=2048):
    return json.dumps(
        {
            "next_question": "When exactly did this happen?",
            "rationale": "The event date determines whether BNS or IPC applies.",
            "sufficient": False,
            "sufficiency_reason": "",
        }
    )


def _fake_contradiction_found(self, system, user_content, max_tokens=2048):
    payload = json.loads(user_content)
    ref = payload["prior_items"][0]["ref"]
    return json.dumps({"contradiction_found": True, "contradicts_ref": ref, "explanation": "Dates conflict."})


def _fake_no_contradiction(self, system, user_content, max_tokens=2048):
    return json.dumps({"contradiction_found": False, "contradicts_ref": None, "explanation": ""})


def _seed_case_with_facts(monkeypatch) -> str:
    monkeypatch.setattr(FactExtractionAgent, "_call_model", _fake_fact_extraction)
    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/narrative", json={"narrative": "placeholder narrative"})
    return case_id


def test_next_question_on_empty_case_does_not_call_model():
    case_id = client.post("/cases").json()["id"]
    response = client.post(f"/cases/{case_id}/interview/next-question")
    assert response.status_code == 200
    body = response.json()
    assert body["next_question"]
    assert body["sufficient"] is False


def test_next_question_uses_classification_and_persists_turn(monkeypatch):
    case_id = _seed_case_with_facts(monkeypatch)
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification)
    monkeypatch.setattr(DynamicInterviewAgent, "_call_model", _fake_next_question)

    response = client.post(f"/cases/{case_id}/interview/next-question")
    assert response.status_code == 200
    body = response.json()
    assert body["next_question"] == "When exactly did this happen?"
    assert body["turn_id"]


def test_question_budget_stops_without_calling_model(monkeypatch):
    case_id = _seed_case_with_facts(monkeypatch)
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification)
    monkeypatch.setattr(DynamicInterviewAgent, "_call_model", _fake_next_question)

    for _ in range(INTERVIEW_QUESTION_BUDGET):
        client.post(f"/cases/{case_id}/interview/next-question")

    def _fail_if_called(self, system, user_content, max_tokens=2048):
        raise AssertionError("should not call the model once budget is exhausted")

    monkeypatch.setattr(DynamicInterviewAgent, "_call_model", _fail_if_called)
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fail_if_called)

    response = client.post(f"/cases/{case_id}/interview/next-question")
    assert response.status_code == 200
    body = response.json()
    assert body["sufficient"] is True
    assert body["next_question"] is None
    assert "budget" in body["sufficiency_reason"]


def test_submit_answer_flags_contradiction(monkeypatch):
    case_id = _seed_case_with_facts(monkeypatch)
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification)
    monkeypatch.setattr(DynamicInterviewAgent, "_call_model", _fake_next_question)
    turn = client.post(f"/cases/{case_id}/interview/next-question").json()

    monkeypatch.setattr(DynamicInterviewAgent, "_call_model", _fake_contradiction_found)
    response = client.post(
        f"/cases/{case_id}/interview/answer", json={"turn_id": turn["turn_id"], "answer": "It happened on a Tuesday."}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["contradiction_found"] is True
    assert body["contradicts_ref"]
    assert body["contradiction_explanation"] == "Dates conflict."


def test_submit_answer_no_contradiction(monkeypatch):
    case_id = _seed_case_with_facts(monkeypatch)
    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _fake_classification)
    monkeypatch.setattr(DynamicInterviewAgent, "_call_model", _fake_next_question)
    turn = client.post(f"/cases/{case_id}/interview/next-question").json()

    monkeypatch.setattr(DynamicInterviewAgent, "_call_model", _fake_no_contradiction)
    response = client.post(
        f"/cases/{case_id}/interview/answer", json={"turn_id": turn["turn_id"], "answer": "It happened last week."}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["contradiction_found"] is False
