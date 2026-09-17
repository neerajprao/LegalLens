"""Regression test for a real behavior difference observed with BOTH
providers this project has used (Gemini, then local Ollama/Qwen3.5,
2026-08-26): a model sometimes wraps JSON responses in a markdown code
fence despite every system prompt explicitly saying not to. A bare
json.loads() on a fenced response fails — this proves the shared
_strip_code_fence() helper in base.py actually prevents that, for both
parsing patterns used across the agent files."""

import json

from app.agents.base import _strip_code_fence
from app.agents.fact_extraction import FactExtractionAgent


def test_strip_code_fence_removes_json_fence():
    fenced = '```json\n{"a": 1}\n```'
    assert _strip_code_fence(fenced) == '{"a": 1}'


def test_strip_code_fence_removes_bare_fence():
    fenced = '```\n{"a": 1}\n```'
    assert _strip_code_fence(fenced) == '{"a": 1}'


def test_strip_code_fence_leaves_unfenced_text_unchanged():
    assert _strip_code_fence('{"a": 1}') == '{"a": 1}'


def test_call_model_strips_fence_from_the_real_client_response(monkeypatch):
    """End-to-end through the real _call_model() (not a mock of _call_model
    itself, since that would bypass the very code under test): a fenced
    raw response from the client must come back unfenced, and parse
    successfully on the first _call_model_json attempt with no wasted
    repair-retry call."""
    import httpx

    calls = {"count": 0}
    fenced_content = '```json\n' + json.dumps({"entities": [], "events": [], "statements": []}) + '\n```'

    def _fake_post(url, **kwargs):
        calls["count"] += 1
        return httpx.Response(
            status_code=200,
            json={"message": {"content": fenced_content}},
            request=httpx.Request("POST", "http://fake"),
        )

    agent = FactExtractionAgent()
    monkeypatch.setattr(agent._client, "post", _fake_post)
    result = agent.run({"narrative": "test"})

    assert calls["count"] == 1  # no wasted repair-retry call
    assert result == {"entities": [], "events": [], "statements": []}
