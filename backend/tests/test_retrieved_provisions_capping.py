"""Regression test for a real bug found running Document Generation live
against the local model (Qwen3.5 9B, 2026-08-26): with 3 classification
hypotheses x 5 retrieval hits each, up to 15 (often overlapping, often
irrelevant) provisions were being passed into a single prompt. The model
didn't error -- it lost track of the actual drafting task under that much
noisy context and echoed back a fragment of one of the *input* provisions
as if it were the output. Orchestrator._flatten_retrieved_provisions() now
deduplicates by chunk_id and caps both the count and each provision's text
length before any agent sees it."""

from app.orchestrator import Orchestrator


def _fake_hit(chunk_id: str, section_number: str, text: str = "some section text") -> dict:
    return {
        "chunk_id": chunk_id,
        "text": text,
        "metadata": {"act_name": "BNS_2023", "section_number": section_number},
    }


def test_flatten_deduplicates_by_chunk_id():
    retrieval_result = {
        "retrieved": {
            "criminal intimidation": [_fake_hit("BNS_2023-709", "351")],
            "cybercrime": [_fake_hit("BNS_2023-709", "351")],  # same chunk, different hypothesis
        }
    }
    flat = Orchestrator._flatten_retrieved_provisions(retrieval_result)
    assert len(flat) == 1
    assert flat[0]["chunk_id"] == "BNS_2023-709"


def test_flatten_caps_total_provision_count():
    retrieval_result = {
        "retrieved": {
            f"hypothesis_{i}": [_fake_hit(f"chunk-{i}-{j}", str(i * 10 + j)) for j in range(5)]
            for i in range(3)
        }
    }
    # 3 hypotheses x 5 hits = 15 distinct chunk_ids before capping
    flat = Orchestrator._flatten_retrieved_provisions(retrieval_result)
    assert len(flat) == Orchestrator._MAX_PROVISIONS_FOR_AGENTS
    assert len(flat) < 15


def test_flatten_truncates_long_provision_text():
    long_text = "x" * 5000
    retrieval_result = {"retrieved": {"cat": [_fake_hit("chunk-1", "1", text=long_text)]}}
    flat = Orchestrator._flatten_retrieved_provisions(retrieval_result)
    assert len(flat[0]["text"]) == Orchestrator._MAX_PROVISION_TEXT_CHARS
