from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_case():
    response = client.post("/cases")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["jurisdiction"] == "India - Karnataka"
