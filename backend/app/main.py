import logging

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.document_generation import VALID_DRAFT_TYPES
from app.db import Base, engine, get_db
from app.models import Case
from app.orchestrator import Orchestrator

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


@app.post("/cases/{case_id}/claims")
def create_claim(case_id: str, body: ClaimIn, db: Session = Depends(get_db)) -> dict:
    case = db.get(Case, case_id)
    if case is None:
        return {"error": "case not found"}
    orchestrator = Orchestrator(db)
    return orchestrator.add_claim(case, body.description)


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
