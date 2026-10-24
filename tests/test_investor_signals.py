"""Invented counterexamples only; no real company data, network or model calls."""

import json
from datetime import date
from decimal import Decimal

import httpx
import pytest
from test_equity import EmptyAI, EquityMemoryStore, dataset, numeric_analysis, pdf, report_text
from test_equity_review_v2 import healthy_snapshot

from bilanco.cli import parser
from bilanco.equity_models import COMPANIES, SignalObservation, TextExtraction
from bilanco.equity_pipeline import run_equity
from bilanco.equity_replay import run_replay
from bilanco.equity_rules import evaluate
from bilanco.equity_signals import CATALOG, signal_checks
from bilanco.equity_sources import Dataset, EquityHTTP, accept_kap, acquire, resolve_member
from bilanco.equity_tables import extract_financial
from bilanco.equity_text import validate_extraction
from bilanco.models import Block, Locator


def candidate(data, kind, text, *, assertion="issue", statement_type="issuer_statement"):
    company = COMPANIES["ozatd"].name
    quote = f"SYNTHETIC TEST. {company}\n31.12.2024\nVarlık A: {text}"
    block = Block(id="signal", source_id=data.sources[0].id, line_start=1, text=quote)
    obj = SignalObservation(
        kind=kind,
        company_name=company,
        subject="Varlık A",
        period_end=date(2024, 12, 31),
        event_date=None,
        assertion=assertion,
        statement_type=statement_type,
        evidence=[Locator(block_id=block.id, quote=quote)],
        counter_evidence=[],
    )
    return obj, block


ISSUES = {
    "cash_collection": "Ticari alacak tahsil edilememiştir.",
    "related_receivables": "İlişkili taraf alacağının vadesi uzatılmıştır.",
    "related_terms": "İlişkili varlık alımında onay alınmamıştır.",
    "liquidity": "Kredi sözleşme ihlali bulunmaktadır.",
    "earnings_quality": "Kâr, tek seferlik varlık satış gelirini içermektedir.",
    "execution": "Proje sözleşmesi feshedilmiştir.",
    "proceeds_use": "Halka arz geliri amaç dışında kullanılmıştır.",
    "audit_specific": "Denetçi yeterli kanıt elde edilemediğini belirtmiştir.",
    "report_consistency": "Finansal tabloya sehven hatalı tutar yazılmıştır.",
    "insider_sales": "Ana ortak net satış yaparken aynı dönemde güçlü büyüme açıklanmıştır.",
    "price_operations": "Hacim ve fiyat olağan dışı ayrışmıştır.",
    "exit_concentration": "Açıklanan fon paylarında yoğunlaşma vardır.",
    "closing_pattern": "Kapanış müzayedesinde tekrarlayan yükseliş ve geri dönüş gözlenmiştir.",
    "order_cancellations": "Büyük emirlerin tekrar iptal edildiği açıklanmıştır.",
    "inventory_contracts": "Sözleşme varlıkları tahsil edilememiştir.",
}


@pytest.mark.parametrize("kind", ISSUES)
def test_each_review_family_accepts_only_quoted_specific_statement(settings, kind):
    data = dataset(settings)
    obj, block = candidate(data, kind, ISSUES[kind])
    if kind == "audit_specific":
        obj.statement_type = "auditor_statement"
    *_, rejected, accepted = validate_extraction(
        TextExtraction(claims=[], forecasts=[], holdings=[], signals=[obj]),
        [block],
        data.sources[0],
        COMPANIES["ozatd"].name,
        include_signals=True,
    )
    assert accepted == [obj] and not rejected
    # Candidate extraction is separate from a new, uncalibrated company-risk vote.
    a = healthy_snapshot(settings)
    a.blocks.append(block)
    a.signals = accepted
    _, findings, _, outcome = evaluate(a)
    finding = next(f for f in findings if f.rule_id == "S-" + kind)
    assert finding.level == "review" and not finding.contributes_to_outcome
    assert outcome == "belirgin_isaret_yok"


@pytest.mark.parametrize(
    "kind,text",
    [
        ("related_receivables", "İlişkili taraf alacağı zamanında tahsil edilmiştir."),
        ("cash_collection", "Tahsil edilemeyen alacak bulunmamaktadır."),
        ("liquidity", "Kredi temerrüt durumu bulunmamaktadır."),
        ("execution", "Proje sözleşmesi iptal edilmemiştir."),
        ("proceeds_use", "Halka arz geliri amaç dışında kullanılmamıştır."),
        ("related_terms", "İlişkili varlık için bağımsız değerleme ve onay vardır."),
        ("inventory_contracts", "Stoklar için değer düşüklüğü karşılığı ayrılmıştır."),
        (
            "insider_sales",
            "Ana ortak payları için tipe dönüşüm yapılmıştır, güçlü büyüme beklenmektedir.",
        ),
    ],
)
def test_normal_or_negated_statement_cannot_be_promoted_to_issue(settings, kind, text):
    data = dataset(settings)
    obj, block = candidate(data, kind, text)
    *_, rejected, accepted = validate_extraction(
        TextExtraction(claims=[], forecasts=[], holdings=[], signals=[obj]),
        [block],
        data.sources[0],
        COMPANIES["ozatd"].name,
        include_signals=True,
    )
    assert rejected and not accepted
    assert rejected[0]["candidate"]["subject"] == "Varlık A"


@pytest.mark.parametrize("mutation", ["quote", "issuer", "subject", "future", "unprinted_date"])
def test_signal_cannot_invent_source_identity_or_dates(settings, mutation):
    data = dataset(settings)
    obj, block = candidate(data, "related_receivables", ISSUES["related_receivables"])
    if mutation == "quote":
        obj.evidence[0].quote += " invented extra claim"
    elif mutation == "issuer":
        obj.company_name = "Other Holding A.Ş."
    elif mutation == "subject":
        obj.subject = "Unmentioned Asset"
    else:
        obj.period_end = date(2026, 12, 31) if mutation == "future" else date(2024, 12, 30)
    *_, rejected, accepted = validate_extraction(
        TextExtraction(claims=[], forecasts=[], holdings=[], signals=[obj]),
        [block],
        data.sources[0],
        COMPANIES["ozatd"].name,
        include_signals=True,
    )
    assert rejected and not accepted


@pytest.mark.parametrize("statement_type", ["allegation", "court_decision", "regulatory_action"])
def test_later_legal_or_regulatory_account_is_context_not_predictive_indicator(
    settings, statement_type
):
    data = dataset(settings)
    obj, block = candidate(
        data,
        "related_terms",
        "Mahkeme ilişkili varlık işleminin şirket aleyhine olduğunu bildirmiştir.",
        statement_type=statement_type,
    )
    a = healthy_snapshot(settings)
    a.signals = [obj]
    a.blocks.append(block)
    _, findings, _, outcome = evaluate(a)
    found = next(f for f in findings if f.rule_id == "S-related_terms")
    assert found.level == "context" and not found.contributes_to_outcome
    assert outcome == "belirgin_isaret_yok"


def test_legal_claim_cannot_be_disguised_as_direct_issuer_fact(settings):
    data = dataset(settings)
    obj, block = candidate(
        data,
        "related_terms",
        "Mahkeme ilişkili varlık işleminin şirket aleyhine olduğunu bildirmiştir.",
    )
    *_, rejected, accepted = validate_extraction(
        TextExtraction(claims=[], forecasts=[], holdings=[], signals=[obj]),
        [block],
        data.sources[0],
        COMPANIES["ozatd"].name,
        include_signals=True,
    )
    assert not accepted and rejected[0]["reason"] == "signal_legal_statement_mislabelled"


def test_all_fifteen_checks_export_unknown_instead_of_safe_when_inputs_missing(settings):
    a = numeric_analysis(settings)
    a.facts = []
    a.metrics, findings, coverage, _ = evaluate(a)
    checks = signal_checks(a, findings, coverage)
    assert len(checks) == 15 and {c.id for c in checks} == set(CATALOG)
    assert all(c.status == "unavailable" and c.missing_inputs for c in checks)
    assert "gün içi/emir" in next(c.note for c in checks if c.id == "order_cancellations")


def test_measurement_of_investment_line_prevents_whole_ocf_being_called_cash_burn(settings):
    text = (
        report_text()
        + "Yatirim ya da Finansman Faaliyetlerinden Kaynaklanan Nakit Akislarina Neden Olan Diger Kalemlere Iliskin Duzeltmeler -450 0\n"
    )
    a = numeric_analysis(settings, text)
    metrics, findings, _, _ = evaluate(a)
    values = {m.id: m for m in metrics}
    assert values["cashflow_investment_adjustment_share"].value == Decimal("0.9")
    assert values["cashflow_without_investment_line_sensitivity"].value == -50
    assert "not corrected" in values["cashflow_without_investment_line_sensitivity"].formula
    assert next(f for f in findings if f.rule_id == "F01").level == "context"
    assert not next(f for f in findings if f.rule_id == "F01").contributes_to_outcome
    assert next(f for f in findings if f.rule_id == "F01").counter_evidence


def test_related_balances_and_inventory_use_same_scope_and_explicit_opening_balance(settings):
    text = (
        report_text()
        .replace(
            "Ticari Alacaklar 400 100",
            """Ticari Alacaklar 400 100
- Iliskili Taraflardan Ticari Alacaklar 40 20
- Iliskili Taraflardan Diger Alacaklar 60 30
Stoklar 20 10
Sozlesme Varliklari 50 0""",
        )
        .replace("Hasilat 1.000 2.000", "Hasilat 1.000 2.000\nSatislarin Maliyeti -600 -1.200")
    )
    a = numeric_analysis(settings, text)
    metrics, findings, _, _ = evaluate(a)
    values = {m.id: m.value for m in metrics}
    assert values["current_related_receivables_assets"] == Decimal("0.02")
    assert "noncurrent_related_receivables_assets" not in values
    assert values["inventory_days"] == Decimal("9.15")
    assert values["current_contract_assets_revenue"] == Decimal("0.05")
    assert "cash_plus_current_investments_debt_sensitivity" not in values
    assert values["receivable_average_days"] == Decimal("91.5")
    assert values["cash_conversion_mismatch_periods"] == 1
    # Ratios alone do not assert overdue related funding or abusive transactions.
    assert not any(f.rule_id.startswith("S-") for f in findings)
    a.facts = [f for f in a.facts if not (f.concept == "inventories" and f.period_end.year == 2023)]
    assert "inventory_days" not in {m.id for m in evaluate(a)[0]}


def old_report():
    return (
        report_text("03.03.2016 21:47:48")
        .replace("2024", "2015")
        .replace("2023", "2014")
        .replace("OZATA DENIZCILIK SANAYI VE TICARET A.S.", "KERVANSARAY YATIRIM HOLDING A.S.")
        .replace("Konsolide Olmayan", "Konsolide")
        .replace("TMS 29 satin alma gucu 31.12.2015", "TMS 29 uygulamasina son verilmistir.")
    )


def test_kervn_uses_same_cli_acquisition_and_nominal_statement_rules(settings):
    source, blocks, _ = accept_kap(
        pdf(old_report()), 123, COMPANIES["kervn"], date(2016, 3, 31), settings
    )
    facts, rejected = extract_financial(source, blocks, issuer_identity=COMPANIES["kervn"].identity)
    assert facts and not rejected
    assert all(f.measurement_basis == "nominal" and f.scope == "consolidated" for f in facts)
    a, b = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="kervn",
        as_of=date(2016, 3, 31),
        dataset=Dataset(sources=[source], blocks=blocks),
        codex=EmptyAI(),
    )
    assert a.company_id == "kervn" and a.facts and len(b.signal_checks) == 15
    assert (settings.data_dir / "runs" / a.run_id / "analysis.json").is_file()
    assert (
        "Yatırımcı gözlemleri" in (settings.data_dir / "runs" / a.run_id / "report.md").read_text()
    )
    assert (
        parser().parse_args(["analyze", "--company", "KERVN", "--as-of", "2016-03-31"]).company
        == "kervn"
    )


def test_old_date_alone_does_not_authorize_nominal_basis(settings):
    source, blocks, _ = accept_kap(
        pdf(old_report().replace("TMS 29 uygulamasina son verilmistir.", "")),
        123,
        COMPANIES["kervn"],
        date(2016, 3, 31),
        settings,
    )
    facts, rejected = extract_financial(source, blocks)
    assert not facts and rejected[0]["reason"] == "inflation_basis_unverified"


def test_mixed_nominal_and_inflation_facts_cannot_make_operational_comparison(settings):
    a = numeric_analysis(settings)
    a.facts[-1].measurement_basis = "nominal"
    metrics, findings, coverage, _ = evaluate(a)
    assert coverage["financial"] == coverage["operations"] == "invalid"
    assert all(f.level == "context" for f in findings)
    assert "inventory_days" not in {m.id for m in metrics}


def test_member_resolution_uses_metadata_only_and_verifies_exact_company(settings, monkeypatch):
    monkeypatch.setattr("bilanco.equity_sources.time.sleep", lambda _: None)
    member = "a" * 32  # synthetic route, not a real member ID
    company = COMPANIES["kervn"]
    metadata = [
        {
            "disclosure": {
                "disclosureBasic": {
                    "disclosureIndex": company.identity_disclosure_id,
                    "mkkMemberOid": member,
                    "companyTitle": company.name,
                    "stockCode": company.ticker,
                }
            },
            "disclosureBody": ["FUTURE LEGAL RESULT MUST NOT ENTER EVIDENCE"],
        }
    ]
    requests = []

    def handler(request):
        requests.append(request)
        if "attachment-detail" in request.url.path:
            return httpx.Response(200, json=metadata)
        if request.method == "POST":
            assert json.loads(request.content)["mkkMemberOidList"] == [member]
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        http = EquityHTTP(settings, client=client)
        result = acquire(settings, company, date(2016, 3, 31), http=http)
        assert not result.sources and not result.blocks
        assert not any("FUTURE" in json.dumps(r) for r in result.rejected)
        posts = [json.loads(r.content) for r in requests if r.method == "POST"]
        assert 1 <= len(posts) <= 14  # bounded window, not every year since 1997
        assert max(p["toDate"] for p in posts) == "2016-03-31"
        metadata[0]["disclosure"]["disclosureBasic"]["stockCode"] = "OTHER"
        with pytest.raises(ValueError, match="eşleşmedi"):
            resolve_member(EquityHTTP(settings, refresh=True, client=client), company)


def test_kervn_does_not_inherit_ozata_event_dates(settings):
    with pytest.raises(ValueError, match="KERVN için"):
        run_replay(settings, EquityMemoryStore(), company_id="kervn", study="pre-2025-spk")


def test_grounded_signals_roundtrip_through_full_same_pipeline(settings):
    data = dataset(settings)
    obj, block = candidate(data, "related_receivables", ISSUES["related_receivables"])
    data.blocks.append(block)

    class SignalAI(EmptyAI):
        def ask(self, task, packet, schema, **kwargs):
            self.calls += 1
            assert len(packet["investor_checks"]) == 15
            return TextExtraction(claims=[], forecasts=[], holdings=[], signals=[obj])

    a, b = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=data,
        codex=SignalAI(),
    )
    assert a.signals and b.signal_checks
    found = next(c for c in b.signal_checks if c.id == "related_receivables")
    assert found.status == "evidence_found" and found.finding_ids
    payload = json.loads((settings.data_dir / "runs" / a.run_id / "assessment.json").read_text())
    assert payload["schema_version"] == "tr-assessment-1.3"
    assert payload["signal_checks"]


def test_recent_complete_report_precedes_old_cover_in_ai_budget(settings):
    from bilanco.equity_pipeline import evidence_order

    source = dataset(settings).sources[0]
    old = source.model_copy(
        update={"id": "old", "published_at": source.published_at.replace(year=2024)}
    )
    appendix = source.model_copy(update={"id": "new-appendix", "kind": "financial_attachment"})
    assert evidence_order([old, appendix, source]) == [source, appendix, old]


def test_legacy_full_appendix_needs_dated_heading_and_explicit_nominal_policy(settings):
    source = dataset(settings).sources[0].model_copy(update={"kind": "financial_attachment"})
    text = """SYNTHETIC KERVANSARAY YATIRIM HOLDING A.S.
31 ARALIK 2015 TARIHI ITIBARIYLA KONSOLIDE FINANSAL DURUM TABLOSU
Tutarlar Turk Lirasi (TL) olarak ifade edilmistir.
Donem 31 Aralik 2015 31 Aralik 2014
Donen Varliklar
Nakit ve Nakit Benzerleri 10 5
TMS 29 uygulamasina son verilmistir."""
    block = Block(id="legacy", source_id=source.id, line_start=1, text=text)
    facts, rejected = extract_financial(
        source, [block], issuer_identity=COMPANIES["kervn"].identity
    )
    assert not rejected and len(facts) == 2
    assert facts[0].measurement_basis == "nominal" and facts[0].basis_date == date(2015, 12, 31)


def test_modern_non_application_statement_does_not_prove_inflation_adjustment(settings):
    text = report_text().replace("TMS 29 satin alma gucu 31.12.2024", "TMS 29 uygulanmamistir.")
    data = dataset(settings, text)
    facts, rejected = extract_financial(data.sources[0], data.blocks)
    assert not facts and rejected[0]["reason"] == "inflation_basis_unverified"


def test_generic_audit_responsibility_cannot_be_specific_evidence_limit(settings):
    data = dataset(settings)
    obj, block = candidate(
        data,
        "audit_specific",
        "Denetçi yeterli kanıt elde edilememesi ihtimali için sorumlu değildir.",
        statement_type="auditor_statement",
    )
    *_, rejected, accepted = validate_extraction(
        TextExtraction(claims=[], forecasts=[], holdings=[], signals=[obj]),
        [block],
        data.sources[0],
        COMPANIES["ozatd"].name,
        include_signals=True,
    )
    assert rejected and not accepted


def test_kervn_future_court_result_is_never_in_historical_model_packet(settings):
    source, blocks, _ = accept_kap(
        pdf(old_report()), 123, COMPANIES["kervn"], date(2016, 3, 31), settings
    )
    future = source.model_copy(
        update={
            "id": "later-legal",
            "available_at": source.available_at.replace(year=2025),
            "published_at": source.published_at.replace(year=2025),
        }
    )
    late_block = Block(
        id="later", source_id=future.id, line_start=1, text="FUTURE COURT RESULT: synthetic"
    )
    ai = EmptyAI()
    a, _ = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="kervn",
        as_of=date(2016, 3, 31),
        dataset=Dataset(sources=[source, future], blocks=[*blocks, late_block]),
        codex=ai,
    )
    assert all(s.id != future.id for s in a.sources)
    assert "FUTURE COURT" not in json.dumps(ai.packets)


def test_kervn_invalid_replay_explains_before_any_settings_db_or_data_work(monkeypatch, capsys):
    from bilanco.cli import main

    def forbidden():
        pytest.fail("Invalid study must stop before configuration or external work")

    monkeypatch.setattr("bilanco.cli.Settings.load", forbidden)
    assert main(["replay", "--company", "kervn", "--study", "pre-2025-spk"]) == 2
    assert "KERVN için" in capsys.readouterr().err


def test_old_analysis_payload_loads_without_rewriting_source_file(settings):
    from bilanco.equity_models import EquityAnalysis

    a = numeric_analysis(settings)
    old = a.model_dump(mode="json", exclude={"signals"})
    old["schema_version"] = "tr-analysis-1.1"
    for fact in old["facts"]:
        fact.pop("measurement_basis")
    loaded = EquityAnalysis.model_validate(old)
    assert loaded.signals == [] and loaded.schema_version == "tr-analysis-1.1"
    assert all(f.measurement_basis == "inflation_adjusted" for f in loaded.facts)


def test_general_credit_risk_policy_is_not_overdue_receivable_finding(settings):
    data = dataset(settings)
    obj, block = candidate(
        data,
        "related_receivables",
        "İlişkili alacak tahsil edilememesi ihtimali için risk yönetimi uygulanır.",
    )
    *_, rejected, accepted = validate_extraction(
        TextExtraction(claims=[], forecasts=[], holdings=[], signals=[obj]),
        [block],
        data.sources[0],
        COMPANIES["ozatd"].name,
        include_signals=True,
    )
    assert rejected and not accepted
