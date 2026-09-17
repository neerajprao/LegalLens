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
_SECTION_HEADER_RE = re.compile(r"^[ \t]*(?:Section\s+)?(\d+[A-Z]?)\.[ \t]*(.*)$", re.MULTILINE)
_TITLE_MAX_LEN = 120


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


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raw = path.read_text(errors="ignore")
    return clean_text(raw)


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


def chunk_by_section(text: str) -> list[dict]:
    """Splits on section-header lines and returns each section's number,
    a short title (the text on the header line itself), and its full body
    text up to the next section header."""
    matches = list(_SECTION_HEADER_RE.finditer(text))
    if not matches:
        stripped = text.strip()
        return [{"section_number": "", "section_title": "", "text": stripped}] if stripped else []

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
                "section_title": match.group(2).strip()[:_TITLE_MAX_LEN],
                "text": chunk_text,
            }
        )
    return chunks


def build_chunks_for_file(path: Path, tier_dir: str) -> list[Chunk]:
    meta = TIER_METADATA[tier_dir]
    text = extract_text(path)
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
