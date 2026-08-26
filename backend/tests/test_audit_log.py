from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_claim_and_evidence_creation_are_logged():
    case_id = client.post("/cases").json()["id"]
    claim = client.post(f"/cases/{case_id}/claims", json={"description": "Threats were made"}).json()
    client.post(
        f"/cases/{case_id}/evidence",
        json={"evidence_type": "messages", "description": "Screenshots", "linked_claim_id": claim["id"]},
    )

    entries = client.get(f"/cases/{case_id}/audit-log").json()["entries"]
    event_types = [e["event_type"] for e in entries]

    assert "claim_added" in event_types
    assert "evidence_added" in event_types
    claim_entry = next(e for e in entries if e["event_type"] == "claim_added")
    assert claim_entry["payload"]["claim_id"] == claim["id"]


def test_audit_log_is_ordered_and_empty_for_new_case():
    case_id = client.post("/cases").json()["id"]
    assert client.get(f"/cases/{case_id}/audit-log").json()["entries"] == []

    client.post(f"/cases/{case_id}/claims", json={"description": "First"})
    client.post(f"/cases/{case_id}/claims", json={"description": "Second"})

    entries = client.get(f"/cases/{case_id}/audit-log").json()["entries"]
    assert len(entries) == 2
    assert entries[0]["created_at"] <= entries[1]["created_at"]
    assert entries[0]["summary"] == "Claim added: First"
