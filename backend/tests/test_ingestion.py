from app.ingestion import chunk_by_section, effective_dates_for, page_number_for_offset

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


def test_chunk_by_section_splits_title_from_body_sharing_one_line():
    """Real corpus shape: title and body text run together on the section's
    header line, separated by '.—' or ':--' rather than a newline. The old
    behavior kept the whole line (then hard-truncated it at 120 chars),
    producing a title that was actually half a sentence of body text."""
    text = (
        "103. Punishment for murder .—(1) Whoever commits murder shall be punished with death or\n"
        "imprisonment for life, and shall also be liable to fine.\n"
    )
    chunks = chunk_by_section(text)
    assert chunks[0]["section_title"] == "Punishment for murder."


def test_chunk_by_section_splits_title_from_body_with_colon_dash():
    text = "374. Appeals from convictions:--(1) Any person convicted on a trial held by a High Court.\n"
    chunks = chunk_by_section(text)
    assert chunks[0]["section_title"] == "Appeals from convictions."


def test_chunk_by_section_keeps_clean_title_when_body_is_on_its_own_line():
    chunks = chunk_by_section(SAMPLE_TEXT)
    murder_chunk = next(c for c in chunks if c["section_number"] == "103")
    assert murder_chunk["section_title"] == "Punishment for murder."


def test_chunk_by_section_reports_start_offset():
    chunks = chunk_by_section(SAMPLE_TEXT)
    murder_chunk = next(c for c in chunks if c["section_number"] == "103")
    assert SAMPLE_TEXT[murder_chunk["start_offset"] :].startswith("103. Punishment for murder.")


def test_page_number_for_offset_resolves_to_the_containing_page():
    # Page 1 starts at 0, page 2 at 500, page 3 at 1000.
    offsets = [0, 500, 1000]
    assert page_number_for_offset(offsets, 0) == 1
    assert page_number_for_offset(offsets, 499) == 1
    assert page_number_for_offset(offsets, 500) == 2
    assert page_number_for_offset(offsets, 999) == 2
    assert page_number_for_offset(offsets, 1000) == 3
    assert page_number_for_offset(offsets, 5000) == 3


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
    # The stray "Section 122." line no longer mislabels section 374's text (the original bug
    # this test targets), and now also doesn't survive as its own separate chunk: it shares
    # section_number "122" with the real, much longer "122. Imprisonment in default of
    # security..." chunk, and _drop_table_of_contents_duplicates keeps only the longer one per
    # section number — a side benefit of the TOC-duplicate fix, not a regression.
    assert numbers.count("122") == 1
    section_122 = next(c for c in chunks if c["section_number"] == "122")
    assert section_122["text"].startswith("122.Imprisonment in default of security")


TABLE_OF_CONTENTS_TEXT = """BHARATIYA NYAYA SANHITA, 2023

CHAPTER I
PRELIMINARY

ARRANGEMENT OF SECTIONS

CHAPTER VI
OF OFFENCES AFFECTING THE HUMAN BODY

101. Murder.
104. Punishment for murder by life-convict.

CHAPTER VII
SOME LATER CHAPTER

101. Murder.—Except in the cases hereinafter excepted, culpable homicide is murder,—
(a) if the act by which the death is caused is done with the intention of causing death; or
(b) if the act is done with the intention of causing such bodily injury as the offender knows to be
likely to cause the death of the person to whom the harm is caused.

104. Punishment for murder by life-convict.—Whoever, being under sentence of imprisonment for
life, commits murder, shall be punished with death.
"""


def test_chunk_by_section_drops_table_of_contents_duplicate_in_favor_of_real_section_body():
    """Regression test for a real retrieval bug: the corpus's own Table of
    Contents lists section numbers/titles again before the real section
    text, and the header regex matched both identically — producing a
    useless title-only chunk that outranked the real explanatory section in
    vector search (verified live: a "murder" query returned the 12-char TOC
    entry above the 6,434-char real section). Only the longer, substantive
    chunk per section_number should survive."""
    chunks = chunk_by_section(TABLE_OF_CONTENTS_TEXT)
    numbers = [c["section_number"] for c in chunks]
    assert numbers.count("101") == 1
    assert numbers.count("104") == 1

    section_101 = next(c for c in chunks if c["section_number"] == "101")
    assert "culpable homicide is murder" in section_101["text"]

    section_104 = next(c for c in chunks if c["section_number"] == "104")
    assert "sentence of imprisonment for" in section_104["text"]


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
