"""Phase 7: encryption-at-rest for evidence files (CLAUDE.md §18), scoped
to evidence files only per the user's explicit 2026-08-26 decision — full
SQLCipher DB encryption was judged disproportionate for this local/dev
build and stays undone, tracked as a real, known gap."""

import io

from cryptography.fernet import InvalidToken
from fastapi.testclient import TestClient
from PIL import Image

from app.encryption import decrypt_bytes, encrypt_bytes
from app.main import app

client = TestClient(app)


def test_encrypt_decrypt_round_trips():
    data = b"plaintext evidence content that must never sit on disk unencrypted"
    encrypted = encrypt_bytes(data)
    assert encrypted != data
    assert data not in encrypted
    assert decrypt_bytes(encrypted) == data


def test_decrypt_rejects_plaintext_or_wrong_data():
    """A silent fallback to "treat as plaintext" on a decrypt failure would
    defeat the point of encrypting evidence in the first place — decryption
    must fail loudly on data it didn't encrypt."""
    try:
        decrypt_bytes(b"this was never encrypted")
        assert False, "expected InvalidToken"
    except InvalidToken:
        pass


def test_uploaded_evidence_file_is_encrypted_on_disk():
    """End-to-end: upload a real file through the real endpoint and read
    the actual bytes written to disk — the plaintext content must not be
    recoverable without going through decrypt_bytes()."""
    from pathlib import Path

    from app.config import settings

    evidence_dir = Path(settings.evidence_store_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    before = set(evidence_dir.iterdir())

    case_id = client.post("/cases").json()["id"]
    claim = client.post(f"/cases/{case_id}/claims", json={"description": "test claim"}).json()

    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="white").save(buf, format="PNG")
    plaintext_bytes = buf.getvalue()

    response = client.post(
        f"/cases/{case_id}/evidence/upload",
        data={"evidence_type": "photo", "description": "test photo", "linked_claim_id": claim["id"]},
        files={"file": ("test.png", plaintext_bytes, "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["extraction_confidence"] == "none"  # plain white image, nothing to OCR

    inventory = client.get(f"/cases/{case_id}/evidence").json()["evidence"]
    assert len(inventory) == 1
    assert inventory[0]["has_file"] is True

    after = set(evidence_dir.iterdir())
    new_files = after - before
    assert len(new_files) == 1
    new_file = new_files.pop()
    assert new_file.name.endswith(".enc")

    on_disk_bytes = new_file.read_bytes()

    assert on_disk_bytes != plaintext_bytes
    assert b"PNG" not in on_disk_bytes[:20]  # PNG magic bytes must not appear in cleartext
    assert decrypt_bytes(on_disk_bytes) == plaintext_bytes

    new_file.unlink()
