"""Phase 3 ingestion pipeline (CLAUDE.md §12.6): text extraction, chunking,
metadata tagging, and embedding of the criminal-law document corpus into
ChromaDB.

Chunking here is a regex-based section splitter that captures the section
number and a title line as structured metadata — a step up from a plain text
split, but still a first pass, not the fully structure-aware chunker §12.6
calls for as the real requirement: it assumes a single top-level
"N. <title>" / "Section N. <title>" numbering convention and has no concept
of sub-sections, provisos, or explanations nested under a section, which
Indian statutes routinely have. Those will currently get swallowed into the
parent section's chunk rather than split out. Flagged as a known gap, not
presented as done.

Change detection (CLAUDE.md §12.4's "automated periodic re-check" decision):
a SHA-256 checksum per source file is recorded in CHECKSUM_FILE after each
successful ingest. Re-running ingest_all() skips any file whose checksum is
unchanged (no wasted re-embedding) and re-ingests any file that's new or has
changed — this is the change-DETECTION half of §12.4, not the SCHEDULING
half: there is no cron/background job here, this still has to be run
manually or by an external scheduler. That distinction is deliberate, not
an oversight — scheduling infrastructure is out of scope for a local/dev
build. This checksum also stands in for document-authenticity validation
in a narrow sense: it proves a file hasn't silently changed since last
ingested, but does NOT verify the file matches the actual authoritative
e-Gazette/India Code text — that check isn't built (would need a fetch
against the live source, which acquisition policy deliberately avoids
doing automatically, see CLAUDE.md §12.2).
"""

import bisect
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from app.vector_store import get_collection

RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "criminal-law"
CHECKSUM_FILE = RAW_DIR / ".ingestion_checksums.json"

TIER_METADATA = {
    "01-core-legislation": {"tier": 1, "jurisdiction": "India (central)"},
    "02-central-special-laws": {"tier": 2, "jurisdiction": "India (central)"},
    "03-karnataka-state-laws": {"tier": 3, "jurisdiction": "India - Karnataka"},
}

# CLAUDE.md §12.3's firm data-model requirement: every provision carries
# effective_from/effective_to/repealed_by (or its inverse, successor_of), and
# the Law Retrieval Agent must eventually select by event date, not query
# date. Dates below are best-effort from public enactment/commencement
# knowledge, keyed by act_name (the file stem, matching build_chunks_for_file's
# existing act_name convention) — NOT independently re-verified against
# e-Gazette per document, consistent with CLAUDE.md §12.2's acquisition
# policy (this project doesn't automate fetching the live authoritative
# source). An act with no entry here gets nulls for all three fields rather
# than a guessed date — an absent effective date is more honest than a wrong
# one.
ACT_EFFECTIVE_DATES: dict[str, dict] = {
    "BNS_2023": {"effective_from": "2024-07-01", "effective_to": None, "repealed_by": None, "successor_of": "IPC_1860"},
    "BNSS_2023": {"effective_from": "2024-07-01", "effective_to": None, "repealed_by": None, "successor_of": "CrPC_1973"},
    "BSA_2023": {"effective_from": "2024-07-01", "effective_to": None, "repealed_by": None, "successor_of": "Indian_Evidence_Act_1872"},
    "IPC_1860": {"effective_from": "1862-01-01", "effective_to": "2024-06-30", "repealed_by": "BNS_2023", "successor_of": None},
    "CrPC_1973": {"effective_from": "1974-04-01", "effective_to": "2024-06-30", "repealed_by": "BNSS_2023", "successor_of": None},
    "Indian_Evidence_Act_1872": {"effective_from": "1872-09-01", "effective_to": "2024-06-30", "repealed_by": "BSA_2023", "successor_of": None},
    "POCSO_Act_2012": {"effective_from": "2012-11-14", "effective_to": None, "repealed_by": None, "successor_of": None},
    "NDPS_Act_1985": {"effective_from": "1985-11-14", "effective_to": None, "repealed_by": None, "successor_of": None},
    "UAPA_1967": {"effective_from": "1967-12-30", "effective_to": None, "repealed_by": None, "successor_of": None},
    "IT_Act_2000": {"effective_from": "2000-10-17", "effective_to": None, "repealed_by": None, "successor_of": None},
    "Karnataka_Police_Act_1963": {"effective_from": "1965-01-01", "effective_to": None, "repealed_by": None, "successor_of": None},
    "KCOCA_2000": {"effective_from": "2000-01-03", "effective_to": None, "repealed_by": None, "successor_of": None},
    "Karnataka_Goonda_Act_1985": {"effective_from": "1985-01-01", "effective_to": None, "repealed_by": None, "successor_of": None},
}

_NULL_EFFECTIVE_DATES = {"effective_from": None, "effective_to": None, "repealed_by": None, "successor_of": None}


def effective_dates_for(act_name: str) -> dict:
    """Returns the {effective_from, effective_to, repealed_by, successor_of}
    metadata for an act, or all-null if not in ACT_EFFECTIVE_DATES — an
    unlisted act stays honestly unlabeled rather than defaulting to a
    plausible-looking guess."""
    return dict(ACT_EFFECTIVE_DATES.get(act_name, _NULL_EFFECTIVE_DATES))

# The `\s*` between the section number and its title deliberately excludes newlines
# ([ \t]* only, not \s*) — CLAUDE.md §20/§12.7 test coverage caught a real corpus bug this
# regex used to cause: with \s*, a stray "Section 122." cross-reference line in
# CrPC_1973.pdf's extracted text absorbed the blank line after it AND the entire next
# real section header line ("374. Appeals from convictions...") into ITS OWN "title"
# capture group, which also meant finditer never saw "374." as a separate header match at
# all (its line had already been consumed as part of the prior match) — so section 374's
# real text was mislabeled as belonging to section 122. Restricting the gap to same-line
# whitespace only prevents a header match from ever spanning into a following line.
#
# The optional `(?:\d+\[)?` prefix handles a second real corpus pattern found while fixing
# the TOC-duplicate bug (see _drop_table_of_contents_duplicates): amended/inserted sections
# in several source PDFs (Indian_Evidence_Act_1872, UAPA_1967, NDPS_Act_1985, POCSO_Act_2012,
# Karnataka_Police_Act_1963 — 49 sections total) are printed with a leading footnote-index
# marker, e.g. "2[65A. Special provisions as to evidence relating to electronic record.––..."
# rather than a plain "65A.". Without this prefix, the line didn't start with a digit, so the
# header regex never matched it at all — the real section body silently got absorbed into
# whichever preceding section's chunk happened to still be open, meaning that section was
# unretrievable under its own number. Confirmed live: UAPA_1967's real "15. Terrorist act"
# section text (prefixed "3[15. Terrorist act .—4[(1)] Whoever does any act...") was
# completely un-chunked before this fix — only a Table-of-Contents duplicate and an unrelated
# Schedule list entry both also numbered "15" existed as chunks for that section number.
_SECTION_HEADER_RE = re.compile(r"^[ \t]*(?:\d+\[)?(?:Section\s+)?(\d+[A-Z]?)\.[ \t]*(.*)$", re.MULTILINE)
_TITLE_MAX_LEN = 120

# Many source PDFs run a section's title and its body onto the same extracted line —
# "103. Punishment for murder .—(1) Whoever commits murder shall be punished..." — so the raw
# header-line remainder isn't just a title, it's a title plus however much body text fit before
# the next newline. Indian statutes conventionally mark that title/body boundary with a period
# or colon followed by a dash (".—", ".-", ":--", etc.); cutting there yields the actual title
# ("Punishment for murder.") instead of a sentence fragment truncated at an arbitrary character
# count. When a section's title and body legitimately sit on separate lines (common in a table
# of contents), there's no such delimiter on the header line at all, and the raw text is used
# as-is — this only ever shortens a line that already contains a title/body boundary.
_TITLE_BODY_SPLIT_RE = re.compile(r"^(.*?)\s*[.:]\s*[-–—]+")


def _clean_section_title(raw: str) -> str:
    raw = raw.strip()
    match = _TITLE_BODY_SPLIT_RE.match(raw)
    if match and len(match.group(1).strip()) >= 3:
        return match.group(1).strip().rstrip(".:") + "."
    if len(raw) <= _TITLE_MAX_LEN:
        return raw
    truncated = raw[:_TITLE_MAX_LEN].rsplit(" ", 1)[0].strip()
    return (truncated or raw[:_TITLE_MAX_LEN]) + "…"


@dataclass
class Chunk:
    text: str
    section_number: str
    section_title: str
    act_name: str
    tier: int
    jurisdiction: str
    source_file: str
    effective_from: str | None = None
    effective_to: str | None = None
    repealed_by: str | None = None
    successor_of: str | None = None
    page_number: int | None = None


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raw = path.read_text(errors="ignore")
    return clean_text(raw)


def extract_text_with_page_offsets(path: Path) -> tuple[str, list[int]]:
    """Like extract_text, but also returns page_offsets: page_offsets[i] is the
    character offset in the returned text where PDF page i+1 (1-indexed, matching
    the #page=N fragment PDF viewers use) begins. Needed so a retrieved chunk can
    link back to the actual page it came from — page boundaries are lost the
    moment per-page text gets joined into one string, so they have to be tracked
    at extraction time, not recovered afterward.

    Non-PDF (.txt) sources have no page concept: returns a single offset (0) so
    callers can treat "page 1" uniformly rather than special-casing None."""
    if path.suffix.lower() != ".pdf":
        return clean_text(path.read_text(errors="ignore")), [0]

    reader = PdfReader(str(path))
    parts: list[str] = []
    offsets: list[int] = []
    cursor = 0
    for page in reader.pages:
        # Cleaned per-page rather than once over the joined document — clean_text's
        # line-filtering/whitespace-collapsing logic doesn't depend on cross-page
        # context, so this is equivalent in substance; minor differences only in
        # exactly how many blank lines collapse at a page boundary.
        page_text = clean_text(page.extract_text() or "")
        offsets.append(cursor)
        parts.append(page_text)
        cursor += len(page_text) + 1  # +1 for the "\n" join below
    return "\n".join(parts), offsets


def page_number_for_offset(page_offsets: list[int], char_offset: int) -> int:
    """1-indexed PDF page number containing the given character offset into the
    text returned by extract_text_with_page_offsets."""
    return bisect.bisect_right(page_offsets, char_offset)


_PAGE_NUMBER_LINE_RE = re.compile(r"^\s*\d{1,4}\s*$")
_EXCESS_BLANK_LINES_RE = re.compile(r"\n{3,}")
_TRAILING_SPACES_RE = re.compile(r"[ \t]+\n")


def clean_text(text: str) -> str:
    """First-pass document cleaning (CLAUDE.md §12.6 pipeline step): strips
    bare page-number-only lines and collapses excess blank lines/trailing
    whitespace left over from PDF text extraction. Deliberately NOT
    stripping gazette masthead/bilingual-header boilerplate (the Hindi
    "vlk/kkj.k" style noise seen in some source PDFs) — that needs
    per-document-format handling to do safely without risking cutting real
    section text, which is out of scope for this pass."""
    lines = [line for line in text.split("\n") if not _PAGE_NUMBER_LINE_RE.match(line)]
    cleaned = "\n".join(lines)
    cleaned = _TRAILING_SPACES_RE.sub("\n", cleaned)
    cleaned = _EXCESS_BLANK_LINES_RE.sub("\n\n", cleaned)
    return cleaned.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_checksums() -> dict[str, str]:
    if not CHECKSUM_FILE.exists():
        return {}
    return json.loads(CHECKSUM_FILE.read_text())


def _save_checksums(checksums: dict[str, str]) -> None:
    CHECKSUM_FILE.write_text(json.dumps(checksums, indent=2, sort_keys=True))


def _drop_table_of_contents_duplicates(chunks: list[dict]) -> list[dict]:
    """Indian statute PDFs conventionally open with a Table of Contents that
    lists every section's number and title again before the substantive
    text — e.g. "101. Murder." on an early page, followed much later by the
    real "101. Murder.—Except in the cases hereinafter excepted, culpable
    homicide is murder,—(a) if..." section body. The section-header regex
    matches both identically, so chunk_by_section previously produced one
    tiny title-only chunk per TOC entry alongside the real section chunk.

    This was not a cosmetic duplicate: verified live against the real
    ingested corpus, a "murder" query returned the 12-character TOC chunk
    ("101. Murder.", page 6) ranked ABOVE the 6,434-character real section
    101 body (page 45) — short, title-only text embeds as a near-exact
    match for a query naming that same topic, so the useless TOC entry was
    winning retrieval and "view in source" was linking to the TOC page
    instead of the actual explanatory text.

    Fix: for each section_number, keep only the chunk with the most text.
    The real section body is always substantially longer than a bare TOC
    line, so this reliably keeps the substantive chunk and drops the
    TOC/index duplicates, without needing to detect "is this a TOC" any
    more specifically than that. Chunks with no section_number (e.g. a
    document with no headers at all) are left untouched, since there's
    nothing to deduplicate against."""
    best_by_section: dict[str, dict] = {}
    unnumbered: list[dict] = []
    for chunk in chunks:
        section_number = chunk["section_number"]
        if not section_number:
            unnumbered.append(chunk)
            continue
        current_best = best_by_section.get(section_number)
        if current_best is None or len(chunk["text"]) > len(current_best["text"]):
            best_by_section[section_number] = chunk
    kept = list(best_by_section.values()) + unnumbered
    kept.sort(key=lambda c: c["start_offset"])
    return kept


def chunk_by_section(text: str) -> list[dict]:
    """Splits on section-header lines and returns each section's number,
    a short title (the text on the header line itself), its full body text
    up to the next section header, and the character offset where it starts
    (so a caller with page_offsets can resolve it to a PDF page number).

    Table-of-contents duplicates (same section_number, much shorter text)
    are dropped — see _drop_table_of_contents_duplicates."""
    matches = list(_SECTION_HEADER_RE.finditer(text))
    if not matches:
        stripped = text.strip()
        return [{"section_number": "", "section_title": "", "text": stripped, "start_offset": 0}] if stripped else []

    chunks = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk_text = text[start:end].strip()
        if not chunk_text:
            continue
        chunks.append(
            {
                "section_number": match.group(1),
                "section_title": _clean_section_title(match.group(2)),
                "text": chunk_text,
                "start_offset": start,
            }
        )
    return _drop_table_of_contents_duplicates(chunks)


def build_chunks_for_file(path: Path, tier_dir: str) -> list[Chunk]:
    meta = TIER_METADATA[tier_dir]
    text, page_offsets = extract_text_with_page_offsets(path)
    act_name = path.stem
    dates = effective_dates_for(act_name)
    return [
        Chunk(
            text=c["text"],
            section_number=c["section_number"],
            section_title=c["section_title"],
            act_name=act_name,
            tier=meta["tier"],
            jurisdiction=meta["jurisdiction"],
            source_file=path.name,
            page_number=page_number_for_offset(page_offsets, c["start_offset"]),
            **dates,
        )
        for c in chunk_by_section(text)
    ]


def ingest_all(force: bool = False) -> dict:
    """Walks RAW_DIR, chunks every new-or-changed document, and upserts into
    the ChromaDB collection. Unchanged files (same SHA-256 as last run) are
    skipped — this is the change-DETECTION half of CLAUDE.md §12.4's
    "automated periodic re-check" decision (still no scheduler/cron here,
    see module docstring). Pass force=True to re-ingest everything
    regardless of checksum. Returns {"ingested_chunks", "files_processed",
    "files_skipped_unchanged"} instead of a bare count, since "0 chunks"
    used to conflate "nothing downloaded yet" with "everything already
    up to date" — those are different states now."""
    collection = get_collection()
    checksums = _load_checksums()
    total_chunks = 0
    files_processed = 0
    files_skipped = 0

    for tier_dir, meta in TIER_METADATA.items():
        tier_path = RAW_DIR / tier_dir
        if not tier_path.exists():
            continue
        for file_path in sorted(tier_path.glob("*")):
            if file_path.suffix.lower() not in (".pdf", ".txt"):
                continue

            checksum = _sha256(file_path)
            key = str(file_path.relative_to(RAW_DIR))
            if not force and checksums.get(key) == checksum:
                files_skipped += 1
                continue

            chunks = build_chunks_for_file(file_path, tier_dir)
            if not chunks:
                continue

            # upsert only ever adds-or-replaces the ids it's given; it never removes an id
            # that existed before but isn't produced this time. Since chunk_by_section's
            # output for a given file can legitimately shrink between runs (e.g. the
            # TOC-duplicate fix below reduced this corpus from ~5,100 to ~2,700 chunks), a
            # re-ingest without this delete left every id beyond the new, smaller count
            # sitting in the collection as stale leftover duplicates from before — confirmed
            # live: a force re-ingest after that fix still reported 5,136 chunks in the
            # collection, not the ~2,748 the new chunker actually produced, because old
            # higher-numbered ids for BNS_2023 (and everything else) were never cleared.
            existing = collection.get(where={"source_file": file_path.name})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])

            ids = [f"{file_path.stem}-{i}" for i in range(len(chunks))]
            collection.upsert(
                ids=ids,
                documents=[c.text for c in chunks],
                metadatas=[
                    {
                        "act_name": c.act_name,
                        "section_number": c.section_number,
                        "section_title": c.section_title,
                        "tier": c.tier,
                        "jurisdiction": c.jurisdiction,
                        "source_file": c.source_file,
                        "page_number": c.page_number or 0,
                        # ChromaDB metadata values must be str/int/float/bool, not None —
                        # "" stands in for "not known" (CLAUDE.md §12.3), same convention
                        # section_number/section_title already use above.
                        "effective_from": c.effective_from or "",
                        "effective_to": c.effective_to or "",
                        "repealed_by": c.repealed_by or "",
                        "successor_of": c.successor_of or "",
                    }
                    for c in chunks
                ],
            )
            total_chunks += len(chunks)
            files_processed += 1
            checksums[key] = checksum

    _save_checksums(checksums)
    return {"ingested_chunks": total_chunks, "files_processed": files_processed, "files_skipped_unchanged": files_skipped}


if __name__ == "__main__":
    result = ingest_all()
    print(
        f"Ingested {result['ingested_chunks']} chunks from {result['files_processed']} file(s); "
        f"skipped {result['files_skipped_unchanged']} unchanged file(s). Source: {RAW_DIR}"
    )
