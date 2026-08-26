import io

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app

client = TestClient(app)


def _make_text_image_bytes(text: str) -> bytes:
    img = Image.new("RGB", (500, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_upload_image_evidence_extracts_real_text_via_ocr():
    """No mocking — this runs real tesseract OCR against a real generated
    image, proving extraction actually works in this environment, not just
    that the code compiles."""
    case_id = client.post("/cases").json()["id"]
    image_bytes = _make_text_image_bytes("Threatening Message Screenshot")

    response = client.post(
        f"/cases/{case_id}/evidence/upload",
        data={"evidence_type": "screenshot", "description": "Test upload"},
        files={"file": ("evidence.png", image_bytes, "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert "Threatening" in body["extracted_text"]
    assert body["extraction_confidence"] in ("high", "medium", "low")


def test_upload_text_pdf_gets_high_confidence():
    case_id = client.post("/cases").json()["id"]
    # Minimal valid text-based PDF with real extractable text, hand-built (not
    # rendered) so this test has no external dependency beyond pypdf itself.
    pdf_bytes = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/MediaBox[0 0 200 100]/Contents 5 0 R>>endobj\n"
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"5 0 obj<</Length 44>>stream\nBT /F1 12 Tf 10 50 Td (Case Evidence Text) Tj ET\nendstream\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    )

    response = client.post(
        f"/cases/{case_id}/evidence/upload",
        data={"evidence_type": "document", "description": "Test PDF"},
        files={"file": ("evidence.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert "Case Evidence Text" in body["extracted_text"]
    assert body["extraction_confidence"] == "high"
