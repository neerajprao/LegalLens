import json

import app.ingestion as ingestion_module
from app.ingestion import _load_checksums, _sha256


def test_sha256_changes_when_file_content_changes(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("original content")
    first = _sha256(f)

    f.write_text("changed content")
    second = _sha256(f)

    assert first != second


def test_checksum_roundtrip(tmp_path, monkeypatch):
    checksum_file = tmp_path / ".checksums.json"
    monkeypatch.setattr(ingestion_module, "CHECKSUM_FILE", checksum_file)

    ingestion_module._save_checksums({"foo.pdf": "abc123"})
    loaded = _load_checksums()

    assert loaded == {"foo.pdf": "abc123"}
    assert json.loads(checksum_file.read_text()) == {"foo.pdf": "abc123"}


def test_load_checksums_returns_empty_dict_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion_module, "CHECKSUM_FILE", tmp_path / "does-not-exist.json")
    assert _load_checksums() == {}


def test_clean_text_strips_page_numbers_and_excess_blank_lines():
    raw = "Section 1.\nSome text here.\n\n\n\n42\n\nMore text after page number."
    cleaned = ingestion_module.clean_text(raw)

    assert "42" not in cleaned.split("\n")
    assert "\n\n\n" not in cleaned
    assert "Some text here." in cleaned
    assert "More text after page number." in cleaned
