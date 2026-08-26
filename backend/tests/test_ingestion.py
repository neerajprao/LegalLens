from app.ingestion import chunk_by_section

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
