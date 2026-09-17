import io
import json

from fastapi.testclient import TestClient
from PIL import Image

from app.agents.evidence_gap_analysis import EvidenceGapAnalysisAgent
from app.main import app

client = TestClient(app)


def _fake_call_model(self, system, user_content, max_tokens=2048):
    claims = json.loads(user_content)["claims"]
    return json.dumps(
        {"suggestions": [{"claim_id": c["claim_id"], "suggested_evidence_types": ["witness statement"]} for c in claims]}
    )


def test_disputed_evidence_marks_claim_disputed(monkeypatch):
    monkeypatch.setattr(EvidenceGapAnalysisAgent, "_call_model", _fake_call_model)
    case_id = client.post("/cases").json()["id"]
    claim = client.post(f"/cases/{case_id}/claims", json={"description": "Assault occurred"}).json()
    evidence = client.post(
        f"/cases/{case_id}/evidence",
        json={"evidence_type": "witness", "description": "Neighbor's account", "linked_claim_id": claim["id"]},
    ).json()

    dispute_response = client.patch(f"/cases/{case_id}/evidence/{evidence['id']}/dispute", json={"disputed": True})
    assert dispute_response.status_code == 200
    assert dispute_response.json()["disputed"] is True

    claim_status = client.post(f"/cases/{case_id}/claims", json={"description": "unrelated"})
    assert claim_status.status_code == 200

    gaps = client.post(f"/cases/{case_id}/evidence-gaps")
    gap = next(g for g in gaps.json()["gaps"] if g["claim_id"] == claim["id"])
    assert gap["evidence_status"] == "disputed"


def test_undisputed_low_confidence_evidence_marks_claim_partially_supported(monkeypatch):
    monkeypatch.setattr(EvidenceGapAnalysisAgent, "_call_model", _fake_call_model)
    case_id = client.post("/cases").json()["id"]
    claim = client.post(f"/cases/{case_id}/claims", json={"description": "A blurry photo shows the threat"}).json()

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buf, format="PNG")
    client.post(
        f"/cases/{case_id}/evidence/upload",
        data={"evidence_type": "photo", "description": "Blurry photo", "linked_claim_id": claim["id"]},
        files={"file": ("blurry.png", buf.getvalue(), "image/png")},
    )

    gaps = client.post(f"/cases/{case_id}/evidence-gaps")
    gap = next(g for g in gaps.json()["gaps"] if g["claim_id"] == claim["id"])
    assert gap["evidence_status"] == "partially_supported"


def test_dispute_unknown_evidence_id_returns_error():
    case_id = client.post("/cases").json()["id"]
    response = client.patch(f"/cases/{case_id}/evidence/not-a-real-id/dispute", json={"disputed": True})
    assert response.status_code == 200
    assert "error" in response.json()


def test_list_evidence_returns_organized_inventory():
    case_id = client.post("/cases").json()["id"]
    claim = client.post(f"/cases/{case_id}/claims", json={"description": "Assault occurred"}).json()
    evidence = client.post(
        f"/cases/{case_id}/evidence",
        json={"evidence_type": "witness", "description": "Neighbor's account", "linked_claim_id": claim["id"]},
    ).json()
    client.patch(f"/cases/{case_id}/evidence/{evidence['id']}/dispute", json={"disputed": True})

    response = client.get(f"/cases/{case_id}/evidence")
    assert response.status_code == 200
    items = response.json()["evidence"]
    assert len(items) == 1
    assert items[0]["id"] == evidence["id"]
    assert items[0]["linked_claim_id"] == claim["id"]
    assert items[0]["disputed"] is True
    assert items[0]["has_file"] is False


def test_list_evidence_on_empty_case_returns_empty_list():
    case_id = client.post("/cases").json()["id"]
    response = client.get(f"/cases/{case_id}/evidence")
    assert response.json()["evidence"] == []
