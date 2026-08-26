import json

from fastapi.testclient import TestClient

from app.agents.question_preparation import QuestionPreparationAgent
from app.main import app

client = TestClient(app)


def _fake_questions(self, system, user_content, max_tokens=2048):
    payload = json.loads(user_content)
    claim_desc = payload["claims"][0]["description"] if payload["claims"] else "the claim"
    return json.dumps(
        {
            "questions": [
                {
                    "question": f"How do you know {claim_desc} happened?",
                    "source": "opposing_side",
                    "suggested_response": None,
                    "gap_note": "No evidence linked to this claim yet — cannot construct a grounded response.",
                },
                {
                    "question": "When did the incident occur?",
                    "source": "investigator",
                    "suggested_response": "Based on the recorded event, it occurred as stated in the case timeline.",
                    "gap_note": "",
                },
            ],
            "insufficient_case_state": False,
        }
    )


def test_prepare_questions_flags_ungrounded_gaps(monkeypatch):
    monkeypatch.setattr(QuestionPreparationAgent, "_call_model", _fake_questions)

    case_id = client.post("/cases").json()["id"]
    client.post(f"/cases/{case_id}/claims", json={"description": "Threats were made"})

    response = client.post(f"/cases/{case_id}/questions")
    assert response.status_code == 200
    body = response.json()

    assert body["insufficient_case_state"] is False
    unanswerable = next(q for q in body["questions"] if q["suggested_response"] is None)
    assert "cannot construct" in unanswerable["gap_note"]
    answerable = next(q for q in body["questions"] if q["suggested_response"] is not None)
    assert answerable["source"] == "investigator"


def test_prepare_questions_on_empty_case_does_not_call_model(monkeypatch):
    def _fail_if_called(self, system, user_content, max_tokens=2048):
        raise AssertionError("should not call the model for an empty case state")

    monkeypatch.setattr(QuestionPreparationAgent, "_call_model", _fail_if_called)

    case_id = client.post("/cases").json()["id"]
    response = client.post(f"/cases/{case_id}/questions")

    assert response.status_code == 200
    assert response.json()["insufficient_case_state"] is True
