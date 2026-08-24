"""Phase 3 ingestion pipeline (CLAUDE.md §12.6): text extraction, chunking,
metadata tagging, and embedding of the criminal-law document corpus into
ChromaDB.

Chunking here is a naive regex split on "Section N." / "N." patterns — a
first pass, not the fully structure-aware, section-boundary-respecting
chunker §12.6 calls for as the real requirement. It will mis-split documents
that don't follow this exact numbering convention. Flagged as a known gap,
not presented as done.

Nothing in data/raw/criminal-law/ has been downloaded yet (manual download
per MANIFEST.md), so running this currently ingests zero documents — that's
expected, not a bug. Run again once files are in place.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from app.vector_store import get_collection

RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "criminal-law"

TIER_METADATA = {
    "01-core-legislation": {"tier": 1, "jurisdiction": "India (central)"},
    "02-central-special-laws": {"tier": 2, "jurisdiction": "India (central)"},
    "03-karnataka-state-laws": {"tier": 3, "jurisdiction": "India - Karnataka"},
}

_SECTION_SPLIT_RE = re.compile(r"(?=^\s*(?:Section\s+)?\d+[A-Z]?\.\s)", re.MULTILINE)


@dataclass
class Chunk:
    text: str
    act_name: str
    tier: int
    jurisdiction: str
    source_file: str


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(errors="ignore")


def chunk_by_section(text: str) -> list[str]:
    parts = _SECTION_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def build_chunks_for_file(path: Path, tier_dir: str) -> list[Chunk]:
    meta = TIER_METADATA[tier_dir]
    text = extract_text(path)
    act_name = path.stem
    return [
        Chunk(text=chunk_text, act_name=act_name, tier=meta["tier"], jurisdiction=meta["jurisdiction"], source_file=path.name)
        for chunk_text in chunk_by_section(text)
    ]


def ingest_all() -> int:
    """Walks RAW_DIR, chunks every document found, and upserts into the
    ChromaDB collection. Returns the number of chunks ingested."""
    collection = get_collection()
    total = 0

    for tier_dir, meta in TIER_METADATA.items():
        tier_path = RAW_DIR / tier_dir
        if not tier_path.exists():
            continue
        for file_path in sorted(tier_path.glob("*")):
            if file_path.suffix.lower() not in (".pdf", ".txt"):
                continue
            chunks = build_chunks_for_file(file_path, tier_dir)
            if not chunks:
                continue
            ids = [f"{file_path.stem}-{i}" for i in range(len(chunks))]
            collection.upsert(
                ids=ids,
                documents=[c.text for c in chunks],
                metadatas=[
                    {"act_name": c.act_name, "tier": c.tier, "jurisdiction": c.jurisdiction, "source_file": c.source_file}
                    for c in chunks
                ],
            )
            total += len(chunks)

    return total


if __name__ == "__main__":
    count = ingest_all()
    print(f"Ingested {count} chunks from {RAW_DIR}")
