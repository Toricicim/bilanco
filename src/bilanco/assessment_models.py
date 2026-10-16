"""Evidence-bound review suggestions; independent of the immutable Analysis v1 format."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from .models import Locator, Model

Priority = Literal["first_review", "further_review", "context", "unassessed"]


class EvidenceCheck(Model):
    answer: Literal["yes", "no", "unknown", "conflicting"]
    evidence: list[Locator]


class RelationDraft(Model):
    finding_ids: list[str] = Field(min_length=1)
    company_name: str
    counterparty: str
    executive: str
    kind: Literal[
        "employment", "ownership", "related_transaction", "executive_relationship", "unresolved"
    ]
    classification_evidence: list[Locator] = Field(default_factory=list)
    executive_link: EvidenceCheck
    transaction: EvidenceCheck
    same_parties: EvidenceCheck
    financial_effect: EvidenceCheck
    business_purpose: EvidenceCheck
    controls: EvidenceCheck
    control_basis: Literal[
        "not_found", "management_assertion", "reported_independent", "conflicting"
    ]
    counter_evidence: list[Locator]


class RelationReview(Model):
    cases: list[RelationDraft]


class ReviewCase(Model):
    id: str
    priority: Priority
    rule_id: str
    title: str
    explanation: str
    source_finding_ids: list[str]
    supporting_evidence: list[Locator] = Field(default_factory=list)
    counter_evidence: list[Locator] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    model_assessed: bool = False
    human_reviewed: bool = False
    relation: RelationDraft | None = None


class Assessment(Model):
    schema_version: Literal["1.0"] = "1.0"
    rule_version: Literal["related-party-1"] = "related-party-1"
    id: str
    source_run_id: str
    source_analysis_sha256: str
    company: str
    as_of: date
    created_at: datetime
    status: Literal["complete", "partial", "failed"] = "failed"
    source_analysis_status: str
    cases: list[ReviewCase] = Field(default_factory=list)
    out_of_scope_finding_ids: list[str] = Field(default_factory=list)
    coverage: dict = Field(default_factory=dict)
    rejected: list[dict] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    ai: dict = Field(default_factory=dict)
    timings: dict[str, float] = Field(default_factory=dict)
