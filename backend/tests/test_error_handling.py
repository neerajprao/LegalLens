from fastapi.testclient import TestClient

from app.agents.fact_extraction import FactExtractionAgent
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _raise(self, system, user_content, max_tokens=2048):
    raise RuntimeError("simulated agent failure (e.g. missing API key)")


def test_unhandled_exception_returns_clean_json_with_cors_header(monkeypatch):
    monkeypatch.setattr(FactExtractionAgent, "_call_model", _raise)

    case_id = client.post("/cases").json()["id"]
    response = client.post(
        f"/cases/{case_id}/narrative",
        json={"narrative": "test"},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 500
    assert response.json() == {"error": "internal server error"}
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
