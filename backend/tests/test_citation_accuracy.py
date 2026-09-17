"""Phase 6: citation accuracy testing (CLAUDE.md §12.7, §20). Citation
*binding* (does a self-reported chunk_id correspond to something actually
retrieved) was already implemented and tested in Phase 2/3/5
(`Orchestrator._bind_citations()`, `tests/test_legal_strategy.py`,
`tests/test_document_generation.py`). What was still missing is what
CLAUDE.md §12.7 actually asks for: an automated check that the retrieved
*text* genuinely corresponds to what its own citation metadata claims —
binding alone doesn't catch a chunk whose act_name/section_number label is
wrong for the text it's attached to, only that the chunk_id exists at all.

This is a self-consistency check against the REAL ingested corpus (no
mocks, like test_retrieval_accuracy.py) — not a semantic entailment check
against a generated claim (that would need an LLM judge and a working API
key, and stays out of scope here, documented as a known gap below)."""

from app.vector_store import get_collection

_PAGE = 200  # batch size for iterating the full collection via offset


def _iter_all_chunks():
    collection = get_collection()
    total = collection.count()
    offset = 0
    while offset < total:
        batch = collection.get(limit=_PAGE, offset=offset, include=["documents", "metadatas"])
        for doc, meta in zip(batch["documents"], batch["metadatas"]):
            yield doc, meta
        offset += _PAGE


def test_every_chunks_own_section_number_appears_in_its_own_text():
    """A minimal but real accuracy guarantee: if a chunk is labeled
    act X, section N, the text N must actually appear at (or very near)
    the start of that chunk's own text — catching a chunker bug that
    mislabels which section a body of text belongs to, which citation
    *binding* alone would never catch (binding only checks that a chunk_id
    was really retrieved, not that its label matches its content)."""
    collection = get_collection()
    assert collection.count() > 0, "corpus must be ingested for this test to be meaningful"

    mismatches = []
    checked = 0
    for doc, meta in _iter_all_chunks():
        section_number = meta.get("section_number", "")
        if not section_number:
            continue
        checked += 1
        # chunk_by_section() starts a chunk's text with either "{number}." or, per
        # _SECTION_HEADER_RE's optional "(?:Section\s+)?" group, "Section {number}."
        # (some source PDFs spell it out) — check the label actually opens the text
        # it's attached to, tolerating that same prefix, not just that the string
        # appears anywhere in a long chunk.
        text = doc.lstrip()
        if text.lower().startswith("section"):
            text = text[len("section") :].lstrip()
        if not text.startswith(section_number):
            mismatches.append((meta.get("act_name"), section_number, doc[:60]))

    assert checked > 0, "no labeled chunks found — is the corpus ingested?"
    assert mismatches == [], f"{len(mismatches)} chunk(s) whose section_number label doesn't match their own text: {mismatches[:5]}"


def test_known_gap_no_semantic_entailment_check_against_generated_claims():
    """Documents a real, still-open limitation rather than hiding it
    (CLAUDE.md §12.7's OPEN QUESTION on exact mechanism): this test suite
    verifies retrieved chunks are internally self-consistent (above), and
    separately (test_legal_strategy.py, test_document_generation.py) that
    self-reported citations correspond to real retrieved chunk_ids. Neither
    check verifies that a piece of *generated prose* actually accurately
    represents what a correctly-cited section says — that would need
    sentence-level entailment checking (e.g. an LLM-judge pass comparing
    generated text against cited source text), which needs a working
    ANTHROPIC_API_KEY to run meaningfully and is not implemented anywhere
    in this codebase. This test is a marker, not a passing accuracy claim."""
    assert True  # intentionally trivial — see docstring; tracks the gap, doesn't paper over it
