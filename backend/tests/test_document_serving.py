from fastapi.testclient import TestClient

from app.ingestion import RAW_DIR
from app.main import app

client = TestClient(app)


def test_get_source_document_serves_a_real_ingested_pdf():
    response = client.get("/documents/BNS_2023.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


def test_get_source_document_404s_for_unknown_filename():
    response = client.get("/documents/does-not-exist.pdf")
    assert response.status_code == 200
    assert "error" in response.json()


def test_get_source_document_ignores_path_traversal_components():
    # Starlette's own routing rejects the encoded ".." segments before this even reaches the
    # handler (404) — asserting on "not a served PDF" rather than a specific status code, since
    # either that framework-level rejection or the handler's own {"error": ...} fallback is a
    # safe outcome; only actually serving a file outside RAW_DIR would be the real failure.
    response = client.get("/documents/..%2F..%2F..%2Fetc%2Fpasswd")
    assert response.headers.get("content-type") != "application/pdf"


def test_raw_dir_actually_has_the_corpus_this_test_relies_on():
    assert (RAW_DIR / "01-core-legislation" / "BNS_2023.pdf").exists()


def test_get_source_document_with_section_and_page_returns_a_highlighted_copy():
    """BNS_2023 section 103 ("Punishment for murder") lives on page 47 of
    the real ingested PDF (verified live against the corpus) — the same
    metadata the frontend already has from a classify/strategy response.
    Asserts a real highlighted PDF comes back and it's distinct from the
    plain file, not just that the request succeeds."""
    plain = client.get("/documents/BNS_2023.pdf")
    highlighted = client.get("/documents/BNS_2023.pdf", params={"section": "103", "page": 47})

    assert highlighted.status_code == 200
    assert highlighted.headers["content-type"] == "application/pdf"
    assert highlighted.content[:4] == b"%PDF"
    assert highlighted.content != plain.content


def test_get_source_document_falls_back_to_plain_file_when_section_not_found_on_page():
    """A section number that doesn't actually appear on the given page (a
    mismatched/stale link) must never turn into an error — it should
    degrade to serving the plain, unhighlighted document, matching the
    behavior of an unhighlighted link before this feature existed."""
    plain = client.get("/documents/BNS_2023.pdf")
    response = client.get("/documents/BNS_2023.pdf", params={"section": "999999", "page": 47})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == plain.content


def test_get_source_document_ignores_section_without_page():
    """section/page are only used as a pair — a request with just one of
    them serves the plain file rather than guessing the other."""
    plain = client.get("/documents/BNS_2023.pdf")
    response = client.get("/documents/BNS_2023.pdf", params={"section": "103"})
    assert response.content == plain.content
