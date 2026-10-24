"""Point-in-time Turkish equity types, separate from immutable Enron v1 records."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator, model_validator

from .assessment_models import EvidenceCheck, RelationDraft
from .models import Block, Locator, Model

ISTANBUL = ZoneInfo("Europe/Istanbul")
RULE_VERSION = "tr-equity-review-4"
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
    kap_member: str | None = None
    listed_at: date
    identity_disclosure_id: int | None = Field(default=None, gt=0)
    catalog_lookback_days: int = Field(default=1096, ge=90, le=3653)


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
    "kervn": Company(
        id="kervn",
        name="Kervansaray Yatırım Holding A.Ş.",
        identity="kervansaray yatirim holding",
        ticker="KERVN",
        listed_at=date(1997, 7, 24),
        # Routing metadata only. Neither this document's text nor its later events
        # enter a historical evidence packet. The member ID is verified at run time.
        identity_disclosure_id=1487889,
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
    entity_name: str | None = None
    entity_code: str | None = None
    role: Literal["issuer", "related_fund"] = "issuer"

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
    maturity: Literal["current", "noncurrent", "unknown"] = "unknown"
    basis_evidence: list[Locator] = Field(default_factory=list)
    measurement_basis: Literal["inflation_adjusted", "nominal"] = "inflation_adjusted"

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
    observations: list["CorporateObservation"] = Field(default_factory=list)
    signals: list["SignalObservation"] = Field(default_factory=list)
    document_facts: list["DocumentFact"] = Field(default_factory=list)


class DocumentFact(Model):
    """Neutral, quoted inputs. The model does not calculate a discrepancy or a risk score."""

    kind: Literal[
        "fund_position",
        "fund_net_assets",
        "fund_redemption_days",
        "proceeds_plan",
        "proceeds_spent",
        "contract_owner",
    ]
    entity_name: str
    subject: str
    counterparty: str | None
    period_start: date | None
    period_end: date | None
    effective_date: date | None
    value_text: str | None
    currency: Literal["TRY", "USD", "EUR"] | None
    scope: Literal["standalone", "consolidated", "fund", "unknown"]
    measurement_basis: Literal["inflation_adjusted", "nominal", "unknown"]
    basis_date: date | None
    statement_type: Literal[
        "issuer_statement", "auditor_statement", "allegation", "regulatory_action", "court_decision"
    ]
    evidence: list[Locator] = Field(min_length=1)
    value_evidence: Locator | None
    counter_evidence: list[Locator]
    day_basis: Literal["business", "calendar", "unknown"] = "unknown"


class EvidenceComparison(Model):
    id: str
    kind: str
    subject: str
    status: Literal["difference", "consistent", "not_comparable", "context"]
    input_ids: list[str]
    metric_ids: list[str] = Field(default_factory=list)
    explanation: str
    evidence: list[Locator] = Field(default_factory=list)
    counter_evidence: list[Locator] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)


class FundExposure(Model):
    code: str
    period_end: date | None
    position_ids: list[str]
    related_source_ids: list[str] = Field(default_factory=list)
    metric_ids: list[str] = Field(default_factory=list)
    redemption_days: Decimal | None = None
    redemption_day_basis: Literal["business", "calendar", "unknown"] = "unknown"
    missing_inputs: list[str]
    note: str


class CheckTrace(Model):
    id: str
    title: str
    status: Literal["evidence_found", "partial", "unavailable"]
    sources_acquired: int
    sources_scanned: int
    candidates_accepted: int
    candidates_rejected: int
    rejection_reasons: list[str]
    metric_ids: list[str]
    finding_ids: list[str]
    missing_inputs: list[str]


class InvestorReview(Model):
    status: Literal["inceleme_gerekli", "veri_yetersiz", "belirgin_ek_isaret_yok"]
    message: str
    finding_ids: list[str]
    incomplete_checks: list[str]
    limitations: list[str]


class FinancialHistoryPoint(Model):
    period_start: date
    period_end: date
    scope: str
    source_ids: list[str]
    fact_ids: list[str]
    cash_profit: Decimal | None
    profit_positive_cash_negative: bool | None
    note: str


SignalKind = Literal[
    "cash_collection",
    "related_receivables",
    "related_terms",
    "liquidity",
    "earnings_quality",
    "execution",
    "proceeds_use",
    "audit_specific",
    "report_consistency",
    "insider_sales",
    "price_operations",
    "exit_concentration",
    "closing_pattern",
    "order_cancellations",
    "inventory_contracts",
]


class SignalObservation(Model):
    """A source's specific statement, not an AI investment or fraud verdict."""

    kind: SignalKind
    company_name: str
    subject: str
    period_end: date | None
    event_date: date | None
    assertion: Literal["issue", "counterstatement", "unknown"]
    statement_type: Literal[
        "issuer_statement", "auditor_statement", "allegation", "regulatory_action", "court_decision"
    ]
    evidence: list[Locator] = Field(min_length=1)
    counter_evidence: list[Locator]


class SignalCheck(Model):
    id: SignalKind
    title: str
    domain: Domain
    status: Literal["partial", "evidence_found", "unavailable"]
    finding_ids: list[str] = Field(default_factory=list)
    metric_ids: list[str] = Field(default_factory=list)
    missing_inputs: list[str]
    note: str


class CorporateObservation(Model):
    """A disclosed exposure or role, not a fraud claim or an executive conflict verdict."""

    kind: Literal[
        "executive_role",
        "ownership",
        "related_purchase",
        "related_sale",
        "guarantee",
        "asset_transaction",
        "treasury_investment",
    ]
    company_name: str
    counterparty: str
    person: str | None
    period_end: date | None
    effective_date: date | None
    amount_text: str | None
    currency: Literal["TRY", "USD", "EUR"] | None
    basis_date: date | None
    amount_evidence: Locator | None
    evidence: list[Locator] = Field(min_length=1)
    counter_evidence: list[Locator]
    controls: EvidenceCheck
    business_purpose: EvidenceCheck


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
    contributes_to_outcome: bool = True


class EquityAssessment(Model):
    schema_version: Literal[
        "tr-assessment-1.0", "tr-assessment-1.1", "tr-assessment-1.2", "tr-assessment-1.3"
    ] = "tr-assessment-1.3"
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
    review_candidate_ids: list[str] = Field(default_factory=list)
    calibration_status: Literal["not_calibrated"] = "not_calibrated"
    signal_checks: list[SignalCheck] = Field(default_factory=list)
    check_traces: list[CheckTrace] = Field(default_factory=list)
    investor_review: InvestorReview | None = None


class EquityAnalysis(Model):
    schema_version: Literal[
        "tr-analysis-1.0", "tr-analysis-1.1", "tr-analysis-1.2", "tr-analysis-1.3"
    ] = "tr-analysis-1.3"
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
    observations: list[CorporateObservation] = Field(default_factory=list)
    signals: list[SignalObservation] = Field(default_factory=list)
    document_facts: list[DocumentFact] = Field(default_factory=list)
    document_fact_index: dict[str, int] = Field(default_factory=dict)
    comparisons: list[EvidenceComparison] = Field(default_factory=list)
    fund_exposures: list[FundExposure] = Field(default_factory=list)
    financial_history: list[FinancialHistoryPoint] = Field(default_factory=list)
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


class BundleRelatedDocument(BundleDocument):
    """Explicit source routing, not a trusted risk measurement or publication date."""

    fund_code: str = Field(pattern=r"^[A-Z0-9]{3,5}$")
    fund_name: str = Field(min_length=12)
    file: str | None = None


class Bundle(Model):
    schema_version: Literal["1.0"] = "1.0"
    company: str
    documents: list[BundleDocument] = Field(default_factory=list)
    market: list[BundleMarket] = Field(default_factory=list)
    bulletins: list[BundleBulletin] = Field(default_factory=list)
    related_documents: list[BundleRelatedDocument] = Field(default_factory=list, max_length=20)

    @field_validator("company")
    @classmethod
    def supported(cls, value):
        if value.lower() not in COMPANIES:
            raise ValueError("Desteklenmeyen şirket.")
        return value.lower()
