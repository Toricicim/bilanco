"""Point-in-time Turkish equity types, separate from immutable Enron v1 records."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator, model_validator

from .assessment_models import RelationDraft
from .models import Block, Locator, Model

ISTANBUL = ZoneInfo("Europe/Istanbul")
RULE_VERSION = "tr-equity-review-1"
Domain = Literal["financial", "operations", "relations", "audit", "market"]
Outcome = Literal["dikkat_gerektiriyor", "sinirli_isaret", "belirgin_isaret_yok", "yetersiz_veri"]


def cutoff(day: date) -> datetime:
    return datetime.combine(day, time.max, ISTANBUL)


def available_at(value: datetime | date) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Yayın zamanı saat dilimi içermeli.")
        return value
    return datetime.combine(value + timedelta(days=1), time.min, ISTANBUL)


class Company(Model):
    id: str
    name: str
    identity: str
    ticker: str
    kap_member: str
    listed_at: date


COMPANIES = {
    "ozatd": Company(
        id="ozatd",
        name="Özata Denizcilik Sanayi ve Ticaret A.Ş.",
        identity="ozata denizcilik",
        ticker="OZATD",
        kap_member="8acae2c49145e00d019180a20f28221c",
        listed_at=date(2024, 9, 5),
    ),
    "hatsn": Company(
        id="hatsn",
        name="Hat-San Gemi İnşaa Bakım Onarım Deniz Nakliyat Sanayi ve Ticaret A.Ş.",
        identity="hat san gemi",
        ticker="HATSN",
        kap_member="8acae2c586d22c51018a739bad647f5a",
        listed_at=date(2023, 9, 22),
    ),
}


class EquitySource(Model):
    id: str
    disclosure_id: int | None
    url: str
    sha256: str
    retrieved_at: datetime
    published_at: datetime
    available_at: datetime
    publication_proof: str
    provenance: Literal["kap_public", "manual_kap", "spk_public", "manual_spk"]
    path: str
    kind: str
    version_note: str

    @model_validator(mode="after")
    def dated(self):
        if any(t.tzinfo is None for t in (self.published_at, self.available_at, self.retrieved_at)):
            raise ValueError("Kaynak zamanları saat dilimi içermeli.")
        if self.available_at < self.published_at:
            raise ValueError("Kaynak yayımlanmadan kullanılamaz.")
        return self


class FinancialFact(Model):
    id: str
    source_id: str
    concept: str
    period_start: date | None
    period_end: date
    basis_date: date
    scope: Literal["standalone", "consolidated"]
    currency: Literal["TRY"]
    value: Decimal
    scale: int
    evidence: Locator
    header_evidence: Locator

    @model_validator(mode="after")
    def valid_period(self):
        if self.period_start and self.period_start > self.period_end:
            raise ValueError("Dönem başlangıcı bitişten sonra.")
        if self.scale not in (1, 1000, 1_000_000):
            raise ValueError("Desteklenmeyen ölçek.")
        return self


class PriceBar(Model):
    symbol: str
    day: date
    close: Decimal = Field(gt=0)
    volume: Decimal | None = Field(default=None, ge=0)


class MarketSeries(Model):
    symbol: str
    url: str
    retrieved_at: datetime
    sha256: str
    price_basis: Literal["provider_adjusted", "as_traded"]
    bars: list[PriceBar]
    limitations: list[str] = Field(default_factory=list)


class Metric(Model):
    id: str
    domain: Domain
    value: Decimal
    unit: str
    formula: str
    fact_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class Claim(Model):
    kind: Literal[
        "relation",
        "qualified_opinion",
        "adverse_opinion",
        "disclaimer",
        "going_concern",
        "regulatory",
        "counterstatement",
        "operation",
        "disclosure_issue",
    ]
    evidence: list[Locator] = Field(min_length=1)
    counter_evidence: list[Locator]
    relation: RelationDraft | None


class Forecast(Model):
    period_start: date
    period_end: date
    basis_date: date | None
    amount_text: str
    currency: Literal["TRY", "USD", "EUR", "unknown"]
    evidence: list[Locator] = Field(min_length=1)


class Holding(Model):
    holder: str
    effective_date: date
    percentage_text: str
    basis: Literal["capital", "voting", "unknown"]
    evidence: list[Locator] = Field(min_length=1)


class TextExtraction(Model):
    claims: list[Claim]
    forecasts: list[Forecast]
    holdings: list[Holding]


class ReviewFinding(Model):
    id: str
    domain: Domain
    rule_id: str
    level: Literal["context", "review", "critical"]
    title: str
    explanation: str
    metric_ids: list[str] = Field(default_factory=list)
    evidence: list[Locator] = Field(default_factory=list)
    counter_evidence: list[Locator] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    origin: Literal["indicator", "known_regulatory"] = "indicator"


class EquityAssessment(Model):
    schema_version: Literal["tr-assessment-1.0"] = "tr-assessment-1.0"
    rule_version: str = RULE_VERSION
    source_run_id: str
    source_analysis_sha256: str
    company: str
    as_of: date
    outcome: Outcome
    status: Literal["complete", "partial", "failed"]
    findings: list[ReviewFinding]
    coverage: dict[str, str]
    limitations: list[str]


class EquityAnalysis(Model):
    schema_version: Literal["tr-analysis-1.0"] = "tr-analysis-1.0"
    rule_version: str = RULE_VERSION
    run_id: str
    company: str
    company_id: str
    as_of: date
    created_at: datetime
    status: Literal["complete", "partial", "failed"] = "partial"
    sources: list[EquitySource] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list)
    facts: list[FinancialFact] = Field(default_factory=list)
    market: list[MarketSeries] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    forecasts: list[Forecast] = Field(default_factory=list)
    holdings: list[Holding] = Field(default_factory=list)
    rejected: list[dict] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    ai: dict = Field(default_factory=dict)
    timings: dict[str, float] = Field(default_factory=dict)


class BundleDocument(Model):
    disclosure_id: int = Field(gt=0)
    file: str
    detail_file: str | None = None
    attachments: dict[str, str] = Field(default_factory=dict)


class BundleMarket(Model):
    symbol: str
    file: str
    url: str
    price_basis: Literal["provider_adjusted", "as_traded"]


class BundleBulletin(Model):
    file: str
    url: str


class Bundle(Model):
    schema_version: Literal["1.0"] = "1.0"
    company: str
    documents: list[BundleDocument] = Field(default_factory=list)
    market: list[BundleMarket] = Field(default_factory=list)
    bulletins: list[BundleBulletin] = Field(default_factory=list)

    @field_validator("company")
    @classmethod
    def supported(cls, value):
        if value.lower() not in COMPANIES:
            raise ValueError("Desteklenmeyen şirket.")
        return value.lower()
