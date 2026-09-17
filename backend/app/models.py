import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class StatementClassification(str, enum.Enum):
    fact = "fact"
    assumption = "assumption"
    opinion = "opinion"
    allegation = "allegation"
    unknown = "unknown"


class PartyRole(str, enum.Enum):
    user = "user"
    opposing = "opposing"
    witness = "witness"
    third_party = "third_party"
    authority = "authority"


class ClaimStatus(str, enum.Enum):
    unsupported = "unsupported"
    partially_supported = "partially_supported"
    supported = "supported"
    disputed = "disputed"


class DocumentDraftType(str, enum.Enum):
    complaint = "complaint"
    legal_notice = "legal_notice"
    case_summary = "case_summary"
    chronology = "chronology"
    evidence_list = "evidence_list"
    statement = "statement"
    question_set = "question_set"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    status: Mapped[str] = mapped_column(String, default="active")
    jurisdiction: Mapped[str] = mapped_column(String, default="India - Karnataka")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)

    parties: Mapped[list["Party"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    statements: Mapped[list["Statement"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    claims: Mapped[list["Claim"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    evidence_items: Mapped[list["Evidence"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    interview_turns: Mapped[list["InterviewTurn"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="InterviewTurn.created_at"
    )
    audit_log: Mapped[list["AuditLogEntry"]] = relationship(
        cascade="all, delete-orphan", order_by="AuditLogEntry.created_at"
    )


class Party(Base):
    __tablename__ = "parties"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    role: Mapped[PartyRole] = mapped_column(Enum(PartyRole))
    name_or_identifier: Mapped[str] = mapped_column(String)
    relationship_to_user: Mapped[str] = mapped_column(String, default="")

    case: Mapped["Case"] = relationship(back_populates="parties")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    description: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[str] = mapped_column(String, default="")
    is_approximate_date: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str] = mapped_column(String, default="user_statement")
    confidence: Mapped[str] = mapped_column(String, default="unverified")

    case: Mapped["Case"] = relationship(back_populates="events")


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    raw_text: Mapped[str] = mapped_column(Text)
    classification: Mapped[StatementClassification] = mapped_column(Enum(StatementClassification))
    linked_event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id"), nullable=True)
    linked_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), nullable=True)
    interview_turn_ref: Mapped[str] = mapped_column(String, default="")

    case: Mapped["Case"] = relationship(back_populates="statements")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    description: Mapped[str] = mapped_column(Text)
    asserted_by_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), nullable=True)
    status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus), default=ClaimStatus.unsupported)

    case: Mapped["Case"] = relationship(back_populates="claims")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    evidence_type: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    extraction_confidence: Mapped[str] = mapped_column(String, default="")
    linked_claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id"), nullable=True)
    # CLAUDE.md §11.3's second bullet ("Is the linked Evidence itself disputed
    # or of uncertain provenance?") — a real field so Claim.status can
    # actually distinguish "disputed" from "supported"/"unsupported", not a
    # placeholder. Set via PATCH /cases/{id}/evidence/{evidence_id}/dispute;
    # never inferred automatically (no basis for the system to decide
    # something is disputed on its own).
    disputed: Mapped[bool] = mapped_column(default=False)

    case: Mapped["Case"] = relationship(back_populates="evidence_items")


class DocumentDraft(Base):
    __tablename__ = "document_drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    draft_type: Mapped[DocumentDraftType] = mapped_column(Enum(DocumentDraftType))
    content: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(default=_utcnow)
    review_status: Mapped[str] = mapped_column(String, default="ai_draft")


class InterviewTurn(Base):
    """Not in CLAUDE.md §10.2's original conceptual sketch — added to satisfy
    §7's audit-logging requirement ("all interview exchanges... must be
    logged") and §9.3's contradiction-tagging requirement, neither of which
    fit any existing entity there."""

    __tablename__ = "interview_turns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    question: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Not a real FK: a contradiction can point at either a Statement.id or another
    # InterviewTurn.id (polymorphic reference by design, not an oversight).
    contradicts_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    contradiction_explanation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    answered_at: Mapped[datetime | None] = mapped_column(nullable=True)

    case: Mapped["Case"] = relationship(back_populates="interview_turns")


class AuditLogEntry(Base):
    """Append-only log of every material Case Builder change. Deliberately
    doing double duty as both CLAUDE.md §7's audit-logging requirement
    ("all interview exchanges, retrieved sources, and generated outputs...
    logged") and §10.2's unresolved versioning ASSUMPTION TO VALIDATE
    ("should case state be versioned per material change") — rather than
    building two separate mechanisms, one append-only event log answers
    both: "what happened" (audit) and "what did the system know at time T"
    (versioning, reconstructable by replaying entries up to a timestamp).
    This is NOT full state snapshotting/event-sourcing — payload is a
    free-form JSON string describing the one change, not a complete case
    snapshot; reconstructing full state at time T means replaying entries,
    not looking up one row. That's a real limitation, not hidden."""

    __tablename__ = "audit_log_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    event_type: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
