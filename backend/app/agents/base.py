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

    @abstractmethod
    def run(self, case_state: dict[str, Any]) -> dict[str, Any]:
        """Take the current Case Builder state (or the relevant slice of it)
        and return structured output for the orchestrator to merge back in."""
        raise NotImplementedError
