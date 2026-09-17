import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.config import settings

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n(.*)\n```\s*$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    """Both Gemini and local Ollama models have been observed wrapping JSON
    output in a markdown code fence despite every system prompt explicitly
    saying not to — not a hypothetical, seen directly with both providers
    this project has used. A bare json.loads() on a fenced response fails,
    so every agent's parsing (both _call_model_json and the several agents
    still using a bare try/except json.loads) would otherwise wrongly hit
    its parse-error fallback. Stripped once here, at the shared source, so
    every agent benefits regardless of which parsing pattern it uses."""
    match = _CODE_FENCE_RE.match(text.strip())
    return match.group(1) if match else text


class Agent(ABC):
    """Base class for specialist agents. Each agent reads/writes only through
    the orchestrator-owned Case Builder state passed into run(); agents do not
    call each other directly (CLAUDE.md §8.8).

    LLM provider (CLAUDE.md §19, switched 2026-08-26 twice): Anthropic Claude
    API originally -> Google Gemini's free tier (after the Anthropic account
    had no funded credit balance) -> a fully local model (Qwen3.5 9B via
    Ollama) at the user's explicit request to remove the API/network
    dependency entirely. Each switch touched only _call_model()'s internals;
    every agent's `run()` logic and every caller (Orchestrator, tests) has
    been unchanged throughout, since `_call_model`'s signature and return
    type (a plain string) never changed.

    Talks to Ollama's NATIVE /api/chat endpoint directly via `httpx`, not its
    OpenAI-compatibility layer — deliberately. Qwen3.5 is a reasoning model
    (like gemini-3.6-flash was) that otherwise spends its entire output
    budget on hidden "thinking" before any visible answer (observed: a
    200-token budget fully consumed by reasoning with empty content coming
    back). Neither `reasoning_effort` nor `extra_body={"think": False}` is
    honored through Ollama's OpenAI-compatible endpoint for this model —
    only the native endpoint's top-level `"think": false` field actually
    disables it, verified live (a trivial prompt dropped from a botched
    200-token truncation to a clean 4-token real answer in ~0.5s)."""

    name: str

    def __init__(self) -> None:
        self._client = httpx.Client(base_url=settings.ollama_base_url, timeout=120.0)

    def _call_model(self, system: str, user_content: str, max_tokens: int = 2048) -> str:
        response = self._client.post(
            "/api/chat",
            json={
                "model": settings.ollama_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                "think": False,
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
        return _strip_code_fence(content or "")

    def _call_model_json(
        self, system: str, user_content: str, max_tokens: int = 2048, retries: int = 1
    ) -> tuple[dict[str, Any] | None, str]:
        """Calls the model expecting strict JSON back, and retries once with
        a repair instruction if the first response fails to parse — a bare
        `json.loads` with no recovery (the previous behavior across every
        agent) meant one malformed response threw away an otherwise-usable
        model turn. Returns (parsed_dict_or_None, raw_text) so callers can
        fall back to whatever "insufficient/parse_error" shape they already
        use if parsing still fails after retries — this helper doesn't
        invent a fallback shape of its own, since each agent's fallback
        differs slightly.

        Also validates the parsed value is actually a dict, not just valid
        JSON — a real gap found running this live against a local model
        (Qwen3.5 9B, 2026-08-26): every system prompt asks for a JSON
        *object*, but on Document Generation's longest/most complex prompt
        the model once returned a syntactically-valid JSON *array* instead.
        `json.loads` alone doesn't catch that (a list parses fine), so a
        caller doing `parsed.setdefault(...)` or similar dict-only access
        would crash with an unhandled AttributeError — treated here the
        same as a parse failure (triggers the same repair-retry), since a
        wrong-shaped-but-valid response is just as unusable as invalid JSON."""
        raw = self._call_model(system=system, user_content=user_content, max_tokens=max_tokens)
        for attempt in range(retries + 1):
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    raise json.JSONDecodeError(f"expected a JSON object, got {type(parsed).__name__}", raw, 0)
                return parsed, raw
            except json.JSONDecodeError:
                if attempt >= retries:
                    return None, raw
                raw = self._call_model(
                    system=system,
                    user_content=(
                        f"{user_content}\n\n---\n\n"
                        f"Your previous response to the request above was not valid JSON and could not "
                        f"be parsed:\n\n{raw}\n\n"
                        "Respond again with ONLY the corrected, strictly valid JSON — no prose, "
                        "no markdown code fences, matching the exact shape requested above."
                    ),
                    max_tokens=max_tokens,
                )
        return None, raw

    @abstractmethod
    def run(self, case_state: dict[str, Any]) -> dict[str, Any]:
        """Take the current Case Builder state (or the relevant slice of it)
        and return structured output for the orchestrator to merge back in."""
        raise NotImplementedError
