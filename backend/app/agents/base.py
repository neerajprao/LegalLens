import json
from abc import ABC, abstractmethod
from typing import Any

import anthropic

from app.config import settings


class Agent(ABC):
    """Base class for specialist agents. Each agent reads/writes only through
    the orchestrator-owned Case Builder state passed into run(); agents do not
    call each other directly (CLAUDE.md §8.8)."""

    name: str

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def _call_model(self, system: str, user_content: str, max_tokens: int = 2048) -> str:
        response = self._client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

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
        differs slightly."""
        raw = self._call_model(system=system, user_content=user_content, max_tokens=max_tokens)
        for attempt in range(retries + 1):
            try:
                return json.loads(raw), raw
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
