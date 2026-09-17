import logging
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.document_generation import VALID_DRAFT_TYPES
from app.db import Base, engine, get_db
from app.ingestion import RAW_DIR
from app.models import Case
from app.orchestrator import Orchestrator
from app.pdf_highlight import render_highlighted_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("legal_lens")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Legal Lens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Bug found and fixed 2026-08-24: an unhandled exception (e.g. a missing
    ANTHROPIC_API_KEY causing an agent call to raise) was previously left to
    propagate past CORSMiddleware entirely, so the browser reported a
    confusing "blocked by CORS policy" error instead of the real failure —
    confirmed live via a browser smoke test, not just inferred from reading
    the code. This handler logs the real exception server-side and returns a
    clean JSON error with CORS headers still attached, matching the same
    `{"error": ...}` shape every endpoint already uses for handled failures."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    response = JSONResponse(status_code=500, content={"error": "internal server error"})
    origin = request.headers.get("origin")
    if origin == "http://localhost:5173":
        response.headers["Access-Control-Allow-Origin"] = origin
    return response


class NarrativeIn(BaseModel):
    narrative: str


class ClaimIn(BaseModel):
    description: str


class ClaimUpdateIn(BaseModel):
    description: str


class EvidenceIn(BaseModel):
    evidence_type: str
    description: str = ""
    linked_claim_id: str | None = None


class StrategyIn(BaseModel):
    acknowledged: bool = False


class DocumentIn(BaseModel):
    draft_type: str


class InterviewAnswerIn(BaseModel):
    turn_id: str
    answer: str


class EvidenceDisputeIn(BaseModel):
    disputed: bool = True


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


class CaseIn(BaseModel):
    jurisdiction: str | None = None


@app.post("/cases")
def create_case(body: CaseIn | None = None, db: Session = Depends(get_db)) -> dict:
    """CLAUDE.md §9.4: jurisdiction is explicit-input-first — pass
    `jurisdiction` to override the "India - Karnataka" default. Detection
    from narrative facts (the other half of §9.4's decision) happens later,
    in submit_narrative, as a non-binding warning."""
    case = Case(jurisdiction=body.jurisdiction) if body and body.jurisdiction else Case()
    db.add(case)
    db.commit()
    db.refresh(case)
    return {"id": case.id, "status": case.status, "jurisdiction": case.jurisdiction}


@app.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)) -> dict:
    """Lets a client check a locally-remembered case_id still exists before
    resuming it — e.g. after a page reload, or if the dev DB was reset."""
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    return {"id": case.id, "status": case.status, "jurisdiction": case.jurisdiction}


@app.get("/documents/{filename}")
def get_source_document(
    filename: str,
    section: str | None = Query(None),
    page: int | None = Query(None),
):
    """Serves a raw source PDF from the ingested legal corpus so a retrieved
    provision can link straight to it — CLAUDE.md §12.7's "retrieval must be
    traceable to a real source" carried through to the UI, not just the
    ingestion metadata. `filename` is resolved with Path(...).name first (so
    "../../etc/passwd" collapses to just "passwd") and then only matched
    against files that actually exist under RAW_DIR via rglob — a filename
    that isn't a real ingested document 404s rather than serving anything.

    When `section` and `page` are both given (the provision's own metadata,
    already returned to the frontend by classify/strategy/etc.), serves a
    copy with that section's actual text highlighted (see
    app/pdf_highlight.py) instead of the plain file — replacing the old
    approach of a "#page=N&search=term" URL fragment, which only worked in
    Chromium's built-in viewer and only ever highlighted the short title
    string, not the real explanatory passage. Falls back to the plain,
    unhighlighted file if the section can't be located on that page (should
    be rare given page/section come from real ingestion metadata, but PDF
    text extraction can still disagree at the margins — a failed highlight
    attempt should never turn into a broken document link)."""
    safe_name = Path(filename).name
    matches = list(RAW_DIR.rglob(safe_name))
    if not matches:
        return {"error": "document not found"}
    path = matches[0]

    if section and page:
        highlighted = render_highlighted_pdf(path, page, section)
        if highlighted is not None:
            return Response(content=highlighted, media_type="application/pdf")

    return FileResponse(path, media_type="application/pdf")


@app.post("/cases/{case_id}/narrative")
def submit_narrative(case_id: str, body: NarrativeIn, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.submit_narrative(case, body.narrative)
    return {"case_id": case_id, "fact_extraction": result}


@app.post("/cases/{case_id}/classify")
def classify_case(case_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.classify_and_retrieve(case)
    return {"case_id": case_id, **result}


@app.get("/cases/{case_id}/claims")
def list_claims(case_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.list_claims(case)
    return {"case_id": case_id, **result}


@app.post("/cases/{case_id}/claims")
def create_claim(case_id: str, body: ClaimIn, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    return orchestrator.add_claim(case, body.description)


@app.post("/cases/{case_id}/claims/suggest")
def suggest_claims(case_id: str, db: Session = Depends(get_db)) -> dict:
    """Auto-fills claims from the case's known statements/events (CLAUDE.md
    §11.2's claim/fact distinction preserved: these are still real Claim
    rows added to the Case Builder, not a silently-inferred layer on top of
    it) — grounded in, and only in, what's already on record."""
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.suggest_claims(case)
    return {"case_id": case_id, **result}


@app.patch("/cases/{case_id}/claims/{claim_id}")
def update_claim(case_id: str, claim_id: str, body: ClaimUpdateIn, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    return orchestrator.update_claim(case, claim_id, body.description)


@app.delete("/cases/{case_id}/claims/{claim_id}")
def delete_claim(case_id: str, claim_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    return orchestrator.delete_claim(case, claim_id)


@app.post("/cases/{case_id}/evidence")
def create_evidence(case_id: str, body: EvidenceIn, db: Session = Depends(get_db)) -> dict:
    """Metadata-only, no file attached — use POST /cases/{id}/evidence/upload
    for an actual file with text extraction (CLAUDE.md §11.3)."""
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    return orchestrator.add_evidence(case, body.evidence_type, body.description, body.linked_claim_id)


@app.post("/cases/{case_id}/evidence/upload")
async def upload_evidence(
    case_id: str,
    evidence_type: str = Form(...),
    description: str = Form(""),
    linked_claim_id: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    """CLAUDE.md §11.3: accepts a real file, extracts text (PDF text layer
    or image OCR — see app/evidence_extraction.py for exact scope, scanned
    PDFs are NOT covered), and stores an explicit extraction_confidence
    alongside the text so a low-confidence extraction is never silently
    treated as reliable."""
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    file_bytes = await file.read()
    orchestrator = Orchestrator(db)
    return orchestrator.add_evidence_with_file(
        case, evidence_type, description, linked_claim_id, file.filename or "upload", file_bytes
    )


@app.get("/cases/{case_id}/evidence")
def list_evidence(case_id: str, db: Session = Depends(get_db)) -> dict:
    """CLAUDE.md §10.3/§11: the evidence inventory for a case, organized by
    claim linkage/extraction confidence/dispute state — supports a real
    "evidence organization" UI, not just an add-only form."""
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.list_evidence(case)
    return {"case_id": case_id, **result}


@app.patch("/cases/{case_id}/evidence/{evidence_id}/dispute")
def dispute_evidence(case_id: str, evidence_id: str, body: EvidenceDisputeIn, db: Session = Depends(get_db)) -> dict:
    """CLAUDE.md §11.3: flags (or unflags) a piece of evidence as disputed /
    of uncertain provenance, which feeds Claim.status via
    Orchestrator._compute_claim_statuses (see its docstring for the four-way
    status logic)."""
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    return orchestrator.set_evidence_disputed(case, evidence_id, body.disputed)


@app.post("/cases/{case_id}/evidence-gaps")
def evidence_gaps(case_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.evidence_gap_analysis(case)
    return {"case_id": case_id, **result}


@app.post("/cases/{case_id}/devils-advocate")
def devils_advocate(case_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.devils_advocate(case)
    return {"case_id": case_id, **result}


@app.post("/cases/{case_id}/strategy")
def legal_strategy(case_id: str, body: StrategyIn, db: Session = Depends(get_db)) -> dict:
    """CLAUDE.md §8.5: ranked recommendations are gated behind explicit
    acknowledgment of the non-advice disclaimer — nothing is returned
    beyond the disclaimer itself unless body.acknowledged is true."""
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.legal_strategy(case, acknowledged=body.acknowledged)
    return {"case_id": case_id, **result}


@app.post("/cases/{case_id}/documents")
def generate_document(case_id: str, body: DocumentIn, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    if body.draft_type not in VALID_DRAFT_TYPES:
        return {"error": f"invalid draft_type, must be one of {sorted(VALID_DRAFT_TYPES)}"}
    orchestrator = Orchestrator(db)
    result = orchestrator.generate_document(case, body.draft_type)
    return {"case_id": case_id, **result}


@app.post("/cases/{case_id}/interview/next-question")
def interview_next_question(case_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.next_interview_question(case)
    return {"case_id": case_id, **result}


@app.get("/cases/{case_id}/interview/turns")
def interview_turns(case_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.list_interview_turns(case)
    return {"case_id": case_id, **result}


@app.post("/cases/{case_id}/interview/answer")
def interview_answer(case_id: str, body: InterviewAnswerIn, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.submit_interview_answer(case, body.turn_id, body.answer)
    return {"case_id": case_id, **result}


@app.get("/cases/{case_id}/strength")
def case_strength(case_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.case_strength(case)
    return {"case_id": case_id, **result}


@app.get("/cases/{case_id}/audit-log")
def audit_log(case_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.audit_log(case)
    return {"case_id": case_id, **result}


@app.get("/cases/{case_id}/timeline")
def timeline(case_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.timeline(case)
    return {"case_id": case_id, **result}


@app.post("/cases/{case_id}/questions")
def prepare_questions(case_id: str, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    result = orchestrator.prepare_questions(case)
    return {"case_id": case_id, **result}
