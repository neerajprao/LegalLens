"""Renders a copy of a source statute PDF with the retrieved provision's own
text highlighted, so "view in source" lands on the actual explanatory
passage already marked — not just the right page (see ingestion.py's
TOC-duplicate/footnote-marker fixes for that half of the problem) and not
relying on the browser's own "find in page" overlay (the prior approach,
which only worked in Chromium and highlighted every occurrence of a short
title string anywhere on the page, not the passage itself).

Deliberately re-extracts the target page's text with PyMuPDF and re-applies
ingestion.py's own section-header pattern to it, rather than trying to
match the chunk text already stored in ChromaDB (which was extracted by
pypdf) against PyMuPDF's rendering of the same page. The two extractors
disagree on minor formatting (e.g. pypdf inserts "murder .—", PyMuPDF's own
extraction has "murder.—") — confirmed live, this mismatch silently drops
matches if you search PyMuPDF's page for pypdf's chunk text. Re-deriving the
section's span directly from PyMuPDF's own text guarantees every phrase
handed to `page.search_for` was extracted by the same engine doing the
searching, so it actually finds what it's looking for.
"""

import io
import re
from pathlib import Path

import pymupdf

# Same shape as ingestion.py's _SECTION_HEADER_RE (kept independent rather than imported,
# since this only needs the "where does a section start" half, not chunking/title-cleaning).
_HEADER_RE = re.compile(r"^[ \t]*(?:\d+\[)?(?:Section\s+)?(\d+[A-Z]?)\.[ \t]*", re.MULTILINE)

_HIGHLIGHT_COLOR = (1.0, 0.87, 0.28)  # a legible gold/yellow, not pure #ffff00
_MAX_LINES_TO_SEARCH = 40  # bounds worst case for an unusually long section body


def _section_bounds(page_text: str, section_number: str) -> tuple[int, int] | None:
    """Returns (start, end) character offsets of section_number's own text
    within page_text, from its own header to the start of the next detected
    header (or end of text). None if this page's text doesn't contain that
    section at all — callers should fall back to serving the plain page in
    that case rather than erroring, since the caller-provided page_number
    already comes from real ingestion metadata and should be trustworthy,
    but PDF text extraction can still disagree in edge cases."""
    matches = list(_HEADER_RE.finditer(page_text))
    start = next((m.start() for m in matches if m.group(1) == section_number), None)
    if start is None:
        return None
    end = next((m.start() for m in matches if m.start() > start), len(page_text))
    return start, end


def _vertical_band(page: "pymupdf.Page", span_lines: list[str], page_text: str, section_end_offset: int) -> "pymupdf.Rect | None":
    """Restricts highlighting to the page band between this section's own
    header and the start of the next one (or the bottom of the page).
    Without this, a short, generic line from the target section (e.g. "to
    fine.") can also match identical wording that happens to appear in a
    *different* section elsewhere on the same page — confirmed live: BNS
    §103's own "to fine." line spuriously matched inside §106's unrelated
    text further down page 47. Constraining search_for's `clip` to this
    section's own vertical slice makes that a non-issue rather than
    something a line-length heuristic would need to guess at."""
    if not span_lines:
        return None
    top_quads = page.search_for(span_lines[0], quads=True)
    if not top_quads:
        return None
    top_y = min(q.rect.y0 for q in top_quads)

    # section_end_offset points at the character position right after this section's text in
    # page_text — i.e. where the next header (if any) starts. Locate that header's own text to
    # find where this section's band should stop; fall back to the bottom of the page if this
    # was the last section on the page.
    remaining = page_text[section_end_offset:].strip().split("\n", 1)[0].strip()
    bottom_y = page.rect.y1
    if remaining:
        next_quads = page.search_for(remaining, quads=True)
        candidates = [q.rect.y0 for q in next_quads if q.rect.y0 > top_y]
        if candidates:
            bottom_y = min(candidates)

    return pymupdf.Rect(0, top_y, page.rect.x1, bottom_y)


def render_highlighted_pdf(pdf_path: Path, page_number: int, section_number: str) -> bytes | None:
    """Opens pdf_path, finds section_number's own text span on page_number
    (1-indexed), adds a highlight annotation over every line of it, and
    returns the modified PDF as bytes. Returns None if the section couldn't
    be located on that page (caller should fall back to the plain,
    unhighlighted document rather than fail the request)."""
    doc = pymupdf.open(pdf_path)
    try:
        if not (1 <= page_number <= doc.page_count):
            return None
        page = doc[page_number - 1]
        page_text = page.get_text()
        bounds = _section_bounds(page_text, section_number)
        if bounds is None:
            return None
        start, end = bounds
        span = page_text[start:end]

        lines = [line.strip() for line in span.split("\n") if line.strip()][:_MAX_LINES_TO_SEARCH]
        if not lines:
            return None
        clip = _vertical_band(page, lines, page_text, end)

        any_highlighted = False
        for line in lines:
            quads = page.search_for(line, quads=True, clip=clip) if clip else page.search_for(line, quads=True)
            for quad in quads:
                annot = page.add_highlight_annot(quad)
                annot.set_colors(stroke=_HIGHLIGHT_COLOR)
                annot.update()
                any_highlighted = True

        if not any_highlighted:
            return None

        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()
    finally:
        doc.close()
