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

    case: Mapped["Case"] = relationship(back_populates="evidence_items")


class DocumentDraft(Base):
    __tablename__ = "document_drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    draft_type: Mapped[DocumentDraftType] = mapped_column(Enum(DocumentDraftType))
    content: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(default=_utcnow)
    review_status: Mapped[str] = mapped_column(String, default="ai_draft")
