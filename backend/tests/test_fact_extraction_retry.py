import json

from app.agents.fact_extraction import FactExtractionAgent


def test_retries_once_on_malformed_json_and_recovers(monkeypatch):
    calls = {"count": 0}

    def _flaky(self, system, user_content, max_tokens=2048):
        calls["count"] += 1
        if calls["count"] == 1:
            return "not valid json {broken"
        return json.dumps({"entities": [], "events": [], "statements": []})

    monkeypatch.setattr(FactExtractionAgent, "_call_model", _flaky)
    agent = FactExtractionAgent()
    result = agent.run({"narrative": "test narrative"})

    assert calls["count"] == 2
    assert result == {"entities": [], "events": [], "statements": []}
    assert "parse_error" not in result


def test_falls_back_to_parse_error_after_retry_exhausted(monkeypatch):
    def _always_broken(self, system, user_content, max_tokens=2048):
        return "still not json"

    monkeypatch.setattr(FactExtractionAgent, "_call_model", _always_broken)
    agent = FactExtractionAgent()
    result = agent.run({"narrative": "test narrative"})

    assert result["entities"] == []
    assert result["events"] == []
    assert result["statements"] == []
    assert result["parse_error"] == "still not json"
