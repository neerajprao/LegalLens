"""CLAUDE.md §11.3: basic content extraction for text-bearing evidence, with
an explicit confidence/quality indicator (§11's design requirement) so a
low-confidence extraction is never silently treated as reliable downstream.

Scope, stated plainly rather than implied: PDF text-layer extraction
(pypdf) and image OCR (pytesseract) are covered. Scanned PDFs with no text
layer are NOT covered — that needs a PDF-to-image step (poppler/pdf2image),
which isn't installed in this environment. A scanned PDF gets an honest
"low" confidence and empty text, not a silent failure or a false claim of
full OCR coverage.

Takes raw bytes rather than a file path (changed 2026-08-26 alongside
evidence-file encryption at rest, app/encryption.py): extraction now runs
on the plaintext bytes in memory BEFORE they're encrypted and written to
disk, so a plaintext copy of an uploaded evidence file never touches disk
at all, not even transiently.
"""

import io

import pytesseract
from PIL import Image
from pypdf import PdfReader

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


def extract_text_and_confidence(file_bytes: bytes, suffix: str) -> tuple[str, str]:
    """Returns (extracted_text, confidence) where confidence is one of
    "high", "medium", "low", "none" — never a bare number presented as if
    precise, since OCR/extraction confidence at this level of tooling isn't
    that precise (CLAUDE.md §11.3). `suffix` is the lowercased file
    extension (e.g. ".pdf"), since bytes alone carry no filename."""
    suffix = suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(file_bytes)
    if suffix in IMAGE_EXTENSIONS:
        return _extract_image(file_bytes)
    if suffix == ".txt":
        text = file_bytes.decode(errors="ignore")
        return text, ("high" if text.strip() else "none")

    return "", "none"


def _extract_pdf(file_bytes: bytes) -> tuple[str, str]:
    reader = PdfReader(io.BytesIO(file_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        # No text layer — likely a scanned PDF. Not covered (see module docstring).
        return "", "low"
    return text, "high"


def _extract_image(file_bytes: bytes) -> tuple[str, str]:
    image = Image.open(io.BytesIO(file_bytes))
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    word_confidences = [int(c) for c in data["conf"] if c not in ("-1", -1)]
    text = " ".join(w for w in data["text"] if w.strip())

    if not word_confidences or not text.strip():
        return text, "none"

    avg_confidence = sum(word_confidences) / len(word_confidences)
    if avg_confidence >= 80:
        confidence = "high"
    elif avg_confidence >= 50:
        confidence = "medium"
    else:
        confidence = "low"
    return text, confidence
