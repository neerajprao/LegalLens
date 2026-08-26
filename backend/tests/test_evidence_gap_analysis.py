import json

from fastapi.testclient import TestClient

from app.agents.evidence_gap_analysis import EvidenceGapAnalysisAgent
from app.main import app

client = TestClient(app)


def _fake_call_model(self, system, user_content, max_tokens=2048):
    claims = json.loads(user_content)["claims"]
    return json.dumps(
        {
            "suggestions": [
                {"claim_id": c["claim_id"], "suggested_evidence_types": ["witness statement", "CCTV footage"]}
                for c in claims
            ]
        }
    )


def test_evidence_gap_analysis_distinguishes_supported_and_unsupported(monkeypatch):
    monkeypatch.setattr(EvidenceGapAnalysisAgent, "_call_model", _fake_call_model)

    case_id = client.post("/cases").json()["id"]

    supported_claim = client.post(f"/cases/{case_id}/claims", json={"description": "Threatening messages were sent"}).json()
    unsupported_claim = client.post(f"/cases/{case_id}/claims", json={"description": "Assault occurred on a specific date"}).json()

    client.post(
        f"/cases/{case_id}/evidence",
        json={"evidence_type": "messages", "description": "Screenshot of texts", "linked_claim_id": supported_claim["id"]},
    )

    response = client.post(f"/cases/{case_id}/evidence-gaps")
    assert response.status_code == 200
    gaps = {g["claim_id"]: g for g in response.json()["gaps"]}

    assert gaps[supported_claim["id"]]["evidence_status"] == "supported"
    assert gaps[supported_claim["id"]]["linked_evidence_count"] == 1
    assert gaps[unsupported_claim["id"]]["evidence_status"] == "unsupported"
    assert gaps[unsupported_claim["id"]]["linked_evidence_count"] == 0
    assert "witness statement" in gaps[unsupported_claim["id"]]["suggested_evidence_types"]
    # Metadata-only evidence has no extraction_confidence set, so it's not flagged low-confidence.
    assert gaps[supported_claim["id"]]["low_confidence_evidence_ids"] == []


def test_evidence_gap_analysis_flags_low_confidence_extracted_evidence(monkeypatch):
    monkeypatch.setattr(EvidenceGapAnalysisAgent, "_call_model", _fake_call_model)

    case_id = client.post("/cases").json()["id"]
    claim = client.post(f"/cases/{case_id}/claims", json={"description": "A blurry photo shows the threat"}).json()

    # A 1x1 white image OCRs to empty text -> "none" confidence, a real low-confidence case.
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buf, format="PNG")

    upload = client.post(
        f"/cases/{case_id}/evidence/upload",
        data={"evidence_type": "photo", "description": "Blurry photo", "linked_claim_id": claim["id"]},
        files={"file": ("blurry.png", buf.getvalue(), "image/png")},
    )
    assert upload.json()["extraction_confidence"] == "none"

    response = client.post(f"/cases/{case_id}/evidence-gaps")
    gap = next(g for g in response.json()["gaps"] if g["claim_id"] == claim["id"])
    assert upload.json()["id"] in gap["low_confidence_evidence_ids"]
