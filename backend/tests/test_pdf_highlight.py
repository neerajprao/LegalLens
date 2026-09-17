"""Tests app/pdf_highlight.py against the real ingested corpus (like
test_retrieval_accuracy.py and test_citation_accuracy.py — no mocks, this
module has nothing meaningful to mock: its entire job is to actually find
text in a real PDF)."""

import pymupdf

from app.ingestion import RAW_DIR
from app.pdf_highlight import render_highlighted_pdf

BNS_PATH = RAW_DIR / "01-core-legislation" / "BNS_2023.pdf"


def _annotation_count(pdf_bytes: bytes, page_number: int) -> int:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        return sum(1 for _ in doc[page_number - 1].annots())
    finally:
        doc.close()


def test_render_highlighted_pdf_adds_highlight_annotations_on_the_right_page():
    result = render_highlighted_pdf(BNS_PATH, page_number=47, section_number="103")
    assert result is not None
    assert result[:4] == b"%PDF"
    assert _annotation_count(result, page_number=47) > 0


def test_render_highlighted_pdf_only_highlights_the_target_page_not_others():
    result = render_highlighted_pdf(BNS_PATH, page_number=47, section_number="103")
    assert result is not None
    assert _annotation_count(result, page_number=1) == 0


def test_render_highlighted_pdf_returns_none_for_a_section_not_on_that_page():
    result = render_highlighted_pdf(BNS_PATH, page_number=47, section_number="999999")
    assert result is None


def test_render_highlighted_pdf_returns_none_for_an_out_of_range_page():
    result = render_highlighted_pdf(BNS_PATH, page_number=99999, section_number="103")
    assert result is None
