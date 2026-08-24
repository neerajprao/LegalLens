from typing import Any

from app.agents.base import Agent
from app.vector_store import query_provisions


class LawRetrievalAgent(Agent):
    """CLAUDE.md §8.4 hard requirement: no provision is ever surfaced without
    an actual retrieval hit against the ingested knowledge base. This agent
    does not call the LLM at all for retrieval — it queries ChromaDB directly
    and returns exactly what comes back, including nothing."""

    name = "law_retrieval"

    def run(self, case_state: dict[str, Any]) -> dict[str, Any]:
        hypotheses = case_state.get("hypotheses", [])
        results: dict[str, list[dict]] = {}

        for hypothesis in hypotheses:
            category = hypothesis.get("category", "")
            hits = query_provisions(category)
            results[category] = hits

        no_hits = all(len(hits) == 0 for hits in results.values())
        return {
            "retrieved": results,
            "insufficient_data": no_hits,
            "note": (
                "No documents have been ingested into the knowledge base yet — "
                "see data/raw/criminal-law/MANIFEST.md and app/ingestion.py."
                if no_hits
                else ""
            ),
        }
