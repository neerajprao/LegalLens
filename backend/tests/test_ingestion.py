from app.ingestion import chunk_by_section, effective_dates_for

SAMPLE_TEXT = """BHARATIYA NYAYA SANHITA, 2023

CHAPTER I
PRELIMINARY

1. Short title, commencement and application.
This Act may be called the Bharatiya Nyaya Sanhita, 2023.

CHAPTER VI
OF OFFENCES AFFECTING THE HUMAN BODY

103. Punishment for murder.
Whoever commits murder shall be punished with death or imprisonment for life,
and shall also be liable to fine.

103A. Some inserted provision.
This is a hypothetical amendment-inserted section for test purposes.
"""


def test_chunk_by_section_extracts_numbers_and_titles():
    chunks = chunk_by_section(SAMPLE_TEXT)
    numbers = [c["section_number"] for c in chunks]
    assert numbers == ["1", "103", "103A"]


def test_chunk_by_section_captures_title_and_body():
    chunks = chunk_by_section(SAMPLE_TEXT)
    murder_chunk = next(c for c in chunks if c["section_number"] == "103")
    assert murder_chunk["section_title"] == "Punishment for murder."
    assert "imprisonment for life" in murder_chunk["text"]


def test_chunk_by_section_handles_no_headers():
    chunks = chunk_by_section("Just some plain text with no section markers.")
    assert len(chunks) == 1
    assert chunks[0]["section_number"] == ""


def test_chunk_by_section_handles_empty_text():
    assert chunk_by_section("") == []


STRAY_CROSS_REFERENCE_TEXT = """122.Imprisonment in default of security.-(1) If any person ordered to give security under section
106 does not give such security, he shall be committed to prison.

Section 122.

374. Appeals from convictions:--(1) Any person convicted on a trial held by a High Court in its
extraordinary original criminal jurisdiction may appeal to the Supreme Court.
"""


def test_chunk_by_section_does_not_let_a_stray_cross_reference_swallow_the_next_real_section():
    """Regression test for a real corpus bug caught by
    tests/test_citation_accuracy.py: a bare "Section 122." cross-reference
    line, followed by a blank line and then the real "374. Appeals..."
    header, used to get treated as one header match (the old `\\s*` gap
    spanned the newlines), silently mislabeling section 374's text as
    section 122's. The header regex must never let a match's gap span
    into a following line."""
    chunks = chunk_by_section(STRAY_CROSS_REFERENCE_TEXT)
    numbers = [c["section_number"] for c in chunks]
    assert "374" in numbers, f"section 374 must be its own chunk, got {numbers}"
    section_374 = next(c for c in chunks if c["section_number"] == "374")
    assert section_374["text"].startswith("374. Appeals from convictions")
    # The stray "Section 122." line becomes its own tiny (harmless) chunk rather than
    # absorbing section 374's real text — not eliminated, but no longer mislabeling.
    stray_chunk = next(c for c in chunks if c["text"].strip() == "Section 122.")
    assert "374" not in stray_chunk["text"]


def test_effective_dates_for_new_code_has_no_repeal():
    dates = effective_dates_for("BNS_2023")
    assert dates["effective_from"] == "2024-07-01"
    assert dates["effective_to"] is None
    assert dates["repealed_by"] is None
    assert dates["successor_of"] == "IPC_1860"


def test_effective_dates_for_repealed_code_points_to_successor():
    dates = effective_dates_for("IPC_1860")
    assert dates["effective_to"] == "2024-06-30"
    assert dates["repealed_by"] == "BNS_2023"


def test_effective_dates_for_unknown_act_is_all_null():
    dates = effective_dates_for("Some_Unlisted_Act")
    assert dates == {"effective_from": None, "effective_to": None, "repealed_by": None, "successor_of": None}
