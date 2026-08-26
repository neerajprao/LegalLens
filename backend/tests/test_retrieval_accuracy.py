"""Phase 6: retrieval evaluation against a hand-built gold set, run against
the REAL ingested corpus (no mocks — this is the one test file in the suite
that deliberately hits the live ChromaDB collection built from
data/raw/criminal-law/, not a fake). Requires `python -m app.ingestion` to
have been run at least once against the downloaded documents.

14 queries total (expanded 2026-08-24 from an initial 5), every expected
act/section verified by directly inspecting real query output before
writing the assertion — not guessed. Still not exhaustive coverage of the
13-document corpus (CLAUDE.md §20's full gold-standard-set task remains
open), but broad enough now to span BNS, IPC, UAPA, KCOCA, and BSA/Evidence
Act, not just BNS/IPC. It also documents — rather than hides — a real
weakness: queries against POCSO/NDPS return amendment-notice chunks instead
of substantive offence text, because the naive section chunker (CLAUDE.md
§12.6, still not the real structure-aware requirement) doesn't distinguish
"amendment history" boilerplate from actual offence sections in those
documents' particular formatting.
"""

from app.vector_store import query_provisions


def _top_hit_matches(query: str, expected_act: str, expected_section: str) -> bool:
    hits = query_provisions(query, n_results=3)
    return any(h["metadata"].get("act_name") == expected_act and h["metadata"].get("section_number") == expected_section for h in hits)


def test_murder_retrieves_bns_103():
    assert _top_hit_matches("punishment for murder", "BNS_2023", "103")


def test_criminal_intimidation_retrieves_bns_351():
    assert _top_hit_matches("criminal intimidation", "BNS_2023", "351")


def test_theft_retrieves_bns_303():
    assert _top_hit_matches("theft", "BNS_2023", "303")


def test_criminal_intimidation_also_surfaces_historical_ipc_503():
    """Same query should be able to surface both the current (BNS) and
    historical (IPC) provision — CLAUDE.md §12.3's dual-code requirement
    depends on both being retrievable, not just the newest one winning."""
    hits = query_provisions("criminal intimidation", n_results=5)
    act_section_pairs = {(h["metadata"].get("act_name"), h["metadata"].get("section_number")) for h in hits}
    assert ("IPC_1860", "503") in act_section_pairs


def test_unlawful_assembly_retrieves_bns_189_and_historical_ipc_141():
    assert _top_hit_matches("unlawful assembly", "BNS_2023", "189")
    hits = query_provisions("unlawful assembly", n_results=5)
    act_section_pairs = {(h["metadata"].get("act_name"), h["metadata"].get("section_number")) for h in hits}
    assert ("IPC_1860", "141") in act_section_pairs


def test_defamation_retrieves_bns_356_and_historical_ipc_499():
    assert _top_hit_matches("defamation", "BNS_2023", "356")
    hits = query_provisions("defamation", n_results=5)
    act_section_pairs = {(h["metadata"].get("act_name"), h["metadata"].get("section_number")) for h in hits}
    assert ("IPC_1860", "499") in act_section_pairs


def test_stolen_property_retrieves_bns_317():
    assert _top_hit_matches("possession of stolen property", "BNS_2023", "317")


def test_kidnapping_retrieves_ipc_359():
    assert _top_hit_matches("kidnapping", "IPC_1860", "359")


def test_rape_retrieves_bns_63():
    assert _top_hit_matches("rape", "BNS_2023", "63")


def test_cheating_retrieves_bns_318():
    assert _top_hit_matches("cheating", "BNS_2023", "318")


def test_terrorist_act_retrieves_uapa_15():
    assert _top_hit_matches("unlawful activities prevention terrorist act", "UAPA_1967", "15")


def test_electronic_record_admissibility_retrieves_bsa_and_historical_evidence_act():
    assert _top_hit_matches("right to privacy electronic record", "BSA_2023", "81")
    hits = query_provisions("right to privacy electronic record", n_results=5)
    act_section_pairs = {(h["metadata"].get("act_name"), h["metadata"].get("section_number")) for h in hits}
    assert ("Indian_Evidence_Act_1872", "65B") in act_section_pairs


def test_organised_crime_retrieves_kcoca_3():
    assert _top_hit_matches("organised crime punishment", "KCOCA_2000", "3")


def test_known_weakness_pocso_query_does_not_reliably_surface_substantive_offence_text():
    """Documents a real limitation rather than hiding it: querying for the
    actual offence (penetrative sexual assault) tends to surface
    amendment-notice/definitional chunks instead, because POCSO_Act_2012's
    source PDF formats amendment history in a way the naive chunker
    (CLAUDE.md §12.6) doesn't distinguish from substantive section text.
    This test intentionally does NOT assert correct retrieval — it asserts
    the corpus has content at all, and is a marker for future chunker work,
    not a passing accuracy claim."""
    hits = query_provisions("protection of children from sexual offences penetrative sexual assault", n_results=3)
    assert len(hits) > 0  # the corpus responds; whether it's the RIGHT section is the open problem
