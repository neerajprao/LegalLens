"""CLAUDE.md §11.3: basic content extraction for text-bearing evidence, with
an explicit confidence/quality indicator (§11's design requirement) so a
low-confidence extraction is never silently treated as reliable downstream.

Scope, stated plainly rather than implied: PDF text-layer extraction
(pypdf) and image OCR (pytesseract) are covered. Scanned PDFs with no text
layer are NOT covered — that needs a PDF-to-image step (poppler/pdf2image),
which isn't installed in this environment. A scanned PDF gets an honest
"low" confidence and empty text, not a silent failure or a false claim of
full OCR coverage.
"""

from pathlib import Path

import pytesseract
from PIL import Image
from pypdf import PdfReader

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


def extract_text_and_confidence(file_path: Path) -> tuple[str, str]:
    """Returns (extracted_text, confidence) where confidence is one of
    "high", "medium", "low", "none" — never a bare number presented as if
    precise, since OCR/extraction confidence at this level of tooling isn't
    that precise (CLAUDE.md §11.3)."""
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(file_path)
    if suffix in IMAGE_EXTENSIONS:
        return _extract_image(file_path)
    if suffix == ".txt":
        text = file_path.read_text(errors="ignore")
        return text, ("high" if text.strip() else "none")

    return "", "none"


def _extract_pdf(file_path: Path) -> tuple[str, str]:
    reader = PdfReader(str(file_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        # No text layer — likely a scanned PDF. Not covered (see module docstring).
        return "", "low"
    return text, "high"


def _extract_image(file_path: Path) -> tuple[str, str]:
    image = Image.open(file_path)
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
