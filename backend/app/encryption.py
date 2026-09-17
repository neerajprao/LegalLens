"""CLAUDE.md §18's encryption-at-rest design, implemented for evidence files
only (Phase 7, 2026-08-26) — the SQLite DB itself (case/claim/statement
data) stays unencrypted, per the user's explicit scoping decision: full
SQLCipher migration was judged disproportionate for a local-only dev build
with no real user data, while evidence *files* were a genuinely live gap
(file upload with real content on disk shipped in an earlier session).

Key management is deliberately NOT resolved here, consistent with the
original design note in CLAUDE.md §18 — this module picks the simplest
thing that makes local/dev usable (persist an auto-generated key to a local
file) rather than pretending to solve secrets-manager/KMS integration for a
deployment target that doesn't exist yet (CLAUDE.md §19: local/dev only).
"""

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_KEY_FILE = Path(__file__).resolve().parent.parent.parent / "data" / ".evidence_encryption_key"

_fernet: Fernet | None = None


def _load_or_create_key() -> bytes:
    """Uses `settings.evidence_encryption_key` if set (real deployments
    should set this via env var, not rely on the auto-generated file below).
    Otherwise persists an auto-generated key to a local, gitignored file so
    encrypted evidence stays decryptable across process restarts in dev —
    NOT a substitute for real key management (secrets manager / KMS), which
    stays an open question for any deployment beyond local/dev, same as the
    original design note."""
    if settings.evidence_encryption_key:
        return settings.evidence_encryption_key.encode()

    if _KEY_FILE.exists():
        return _KEY_FILE.read_bytes()

    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    _KEY_FILE.write_bytes(key)
    return key


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_or_create_key())
    return _fernet


def encrypt_bytes(data: bytes) -> bytes:
    return _get_fernet().encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    """Raises cryptography.fernet.InvalidToken if `data` wasn't encrypted
    with the current key (wrong/rotated key, or plaintext passed by
    mistake) — callers should not silently swallow this, since a silent
    fallback to "treat as plaintext" would defeat the point of encrypting
    it in the first place."""
    return _get_fernet().decrypt(data)


__all__ = ["encrypt_bytes", "decrypt_bytes", "InvalidToken"]
