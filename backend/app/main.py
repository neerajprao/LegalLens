from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.models import Case
from app.orchestrator import Orchestrator

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Legal Lens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class NarrativeIn(BaseModel):
    narrative: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/cases")
def create_case(db: Session = Depends(get_db)) -> dict:
    case = Case()
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
