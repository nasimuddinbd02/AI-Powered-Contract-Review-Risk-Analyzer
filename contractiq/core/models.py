"""Pydantic data models (SRS Section 5 — Data Models).

These models are the contract between layers: ingestion produces ``Chunk``s,
agents produce ``Clause``s, and the API serialises ``Contract`` / ``QATurn``.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ClauseType(str, enum.Enum):
    """The 10 standard clause types (SRS FR-2)."""

    TERMINATION = "Termination"
    LIABILITY_CAP = "Liability Cap"
    INDEMNIFICATION = "Indemnification"
    IP_OWNERSHIP = "IP Ownership"
    NON_COMPETE = "Non-Compete"
    CONFIDENTIALITY = "Confidentiality"
    PAYMENT_TERMS = "Payment Terms"
    GOVERNING_LAW = "Governing Law"
    DISPUTE_RESOLUTION = "Dispute Resolution"
    AUTO_RENEWAL = "Auto-Renewal"


class RiskLevel(str, enum.Enum):
    """Risk levels (SRS FR-3)."""

    HIGH = "HIGH"      # Red
    MEDIUM = "MEDIUM"  # Yellow
    LOW = "LOW"        # Green

    @property
    def color(self) -> str:
        return {"HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}[self.value]

    @property
    def icon(self) -> str:
        # Icon + colour together satisfy WCAG 2.1 AA (SRS 4.5).
        return {"HIGH": "▲", "MEDIUM": "■", "LOW": "●"}[self.value]


class ChunkRef(BaseModel):
    """A retrieved chunk reference used in Q&A citations (SRS 5.3)."""

    chunk_id: str
    page_num: int
    text: str
    score: float


class Chunk(BaseModel):
    """An embedded text chunk stored in the vector store (SRS FR-1.3)."""

    chunk_id: str = Field(default_factory=_uuid)
    contract_id: str
    page_num: int
    text: str
    section_header: str | None = None
    embedding: list[float] | None = None


class Clause(BaseModel):
    """Clause object (SRS 5.2)."""

    clause_id: str = Field(default_factory=_uuid)
    contract_id: str
    clause_type: ClauseType
    original_text: str
    plain_english_summary: str | None = None
    risk_level: RiskLevel | None = None
    risk_score: float | None = None  # 0–100
    risk_rationale: str | None = None
    negotiation_suggestion: str | None = None
    is_ambiguous: bool = False
    page_references: list[int] = Field(default_factory=list)


class Contract(BaseModel):
    """Contract object (SRS 5.1)."""

    contract_id: str = Field(default_factory=_uuid)
    filename: str
    upload_timestamp: datetime = Field(default_factory=_now)
    page_count: int = 0
    chunk_count: int = 0
    overall_risk_score: float = 0.0  # 0–100
    parties: list[str] = Field(default_factory=list)
    contract_type: str = "Unknown"
    governing_law: str = "Unknown"
    clauses: list[Clause] = Field(default_factory=list)
    status: str = "uploaded"  # uploaded | processing | analyzed | error
    warnings: list[str] = Field(default_factory=list)


class QATurn(BaseModel):
    """QA turn object (SRS 5.3)."""

    turn_id: str = Field(default_factory=_uuid)
    contract_id: str
    user_query: str
    retrieved_chunks: list[ChunkRef] = Field(default_factory=list)
    agent_answer: str = ""
    citations: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=_now)
