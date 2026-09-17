import json

from app.agents.legal_classification import LegalClassificationAgent


def test_retries_once_on_malformed_json_and_recovers(monkeypatch):
    calls = {"count": 0}

    def _flaky(self, system, user_content, max_tokens=2048):
        calls["count"] += 1
        if calls["count"] == 1:
            return "not valid json {broken"
        return json.dumps({"hypotheses": [], "insufficient_facts": True})

    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _flaky)
    agent = LegalClassificationAgent()
    result = agent.run({"statements": [], "events": []})

    assert calls["count"] == 2
    assert result == {"hypotheses": [], "insufficient_facts": True}
    assert "parse_error" not in result


def test_falls_back_to_parse_error_after_retry_exhausted(monkeypatch):
    def _always_broken(self, system, user_content, max_tokens=2048):
        return "still not json"

    monkeypatch.setattr(LegalClassificationAgent, "_call_model", _always_broken)
    agent = LegalClassificationAgent()
    result = agent.run({"statements": [], "events": []})

    assert result["hypotheses"] == []
    assert result["insufficient_facts"] is True
    assert result["parse_error"] == "still not json"
