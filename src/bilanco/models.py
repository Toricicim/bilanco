from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Locator(Model):
    block_id: str
    quote: str


class Block(Model):
    id: str
    source_id: str
    page: int | None = None
    line_start: int
    text: str


class Source(Model):
    id: str
    url: str
    sha256: str
    media_type: str
    retrieved_at: datetime
    path: str
    publication_date: date
    publication_proof: str
    provenance: Literal["sec_original", "archive_copy", "dated_official"]
    version_note: str
    cached: bool = False


class Fact(Model):
    id: str
    concept: str
    period: int
    value: Decimal
    unit: Literal["dollars", "unknown"]
    scale: int
    evidence: Locator
    header_evidence: Locator
    unit_evidence: Locator
    currency_evidence: Locator | None = None
    origin: Literal["table_parser"] = "table_parser"

    @field_validator("value")
    @classmethod
    def finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Finite amount required")
        return value


class Candidate(Model):
    kind: Literal[
        "related_party",
        "executive_conflict",
        "guarantee",
        "credit_trigger",
        "audit_opinion",
        "management_counterstatement",
        "other",
    ]
    block_id: str
    quote: str = Field(min_length=20, max_length=2500)
    actor: str
    counterparty: str


class Extraction(Model):
    candidates: list[Candidate]


class DiscoveryCandidate(Model):
    url: str
    purpose: Literal["original_report", "filing_metadata", "official_disclosure"]


class Discovery(Model):
    sources: list[DiscoveryCandidate] = Field(max_length=5)


class NarrativeItem(Model):
    finding_id: str
    style: Literal["short", "detailed"]


class Narrative(Model):
    items: list[NarrativeItem]


class Finding(Model):
    id: str
    category: str
    status: Literal["signal", "context", "needs_review", "unavailable"]
    title: str
    explanation: str
    fact_ids: list[str] = Field(default_factory=list)
    evidence: list[Locator] = Field(default_factory=list)


class Metric(Model):
    id: str
    period: int
    name: str
    value: Decimal
    unit: str
    formula: str
    fact_ids: list[str]


class Analysis(Model):
    schema_version: str = "1.0"
    run_id: str
    company: str
    as_of: date
    status: Literal["complete", "partial", "failed"]
    created_at: datetime
    sources: list[Source] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    rejected: list[dict] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    ai: dict = Field(default_factory=dict)
    timings: dict[str, float] = Field(default_factory=dict)
    overall: str = "yetersiz_veri"
