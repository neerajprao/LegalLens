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


def test_wrong_shaped_but_valid_json_is_treated_as_a_parse_failure(monkeypatch):
    """Regression test for a real bug found running the local model
    (Qwen3.5 9B) live, 2026-08-26: a response can be syntactically valid
    JSON (e.g. a bare array) while still being the wrong shape for every
    agent, which expects a JSON *object*. json.loads() alone doesn't catch
    that. _call_model_json must treat a non-dict result the same as
    invalid JSON -- retrying, then falling back to parse_error -- not let
    it through and crash whatever the caller does with dict-only access."""

    def _returns_a_json_array(self, system, user_content, max_tokens=2048):
        return '["not", "a", "dict"]'

    monkeypatch.setattr(FactExtractionAgent, "_call_model", _returns_a_json_array)
    agent = FactExtractionAgent()
    result = agent.run({"narrative": "test narrative"})

    assert result["entities"] == []
    assert "parse_error" in result
