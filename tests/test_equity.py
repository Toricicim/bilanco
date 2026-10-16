"""Invented data only. No financial download or actual model call in these tests."""

import io
import json
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest
from conftest import MemoryStore
from reportlab.pdfgen import canvas

from bilanco.equity_models import (
    COMPANIES,
    ISTANBUL,
    Bundle,
    Claim,
    EquityAnalysis,
    TextExtraction,
    available_at,
    cutoff,
)
from bilanco.equity_pipeline import canonical_hash, run_equity
from bilanco.equity_replay import run_replay, snapshot_dates
from bilanco.equity_rules import evaluate
from bilanco.equity_sources import (
    Dataset,
    EquityHTTP,
    accept_attachment,
    accept_kap,
    acquire,
    attachment_metadata,
    local_file,
    read_market_csv,
    safe_url,
    yahoo_series,
)
from bilanco.equity_tables import extract_financial, parse_turkish
from bilanco.equity_text import validate_extraction
from bilanco.models import Block, Locator


class EquityMemoryStore(MemoryStore):
    def finish_equity(self, analysis, assessment):
        assert assessment.source_analysis_sha256 == canonical_hash(analysis)
        self.runs[analysis.run_id] = (analysis, assessment)

    def save_replay(self, result):
        self.replay = result


class EmptyAI:
    def __init__(self):
        self.calls = 0
        self.receipts = []
        self.packets = []

    def ask(self, task, packet, schema, *, discovery=False):
        assert discovery is False
        self.calls += 1
        self.packets.append(packet)
        return TextExtraction(claims=[], forecasts=[], holdings=[])


def pdf(text):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(1000, 1400))
    y = 1375
    for line in text.splitlines():
        if y < 30:
            c.showPage()
            y = 1375
        c.drawString(20, y, line)
        y -= 14
    c.save()
    return buffer.getvalue()


def report_text(published="03.03.2025 21:47:48", index=123):
    return f"""SYNTHETIC TEST DATA - NOT AN ACTUAL FINANCIAL REPORT
31.12.2024 DONEMI FINANSAL RAPOR
OZATA DENIZCILIK SANAYI VE TICARET A.S.
Konsolide Olmayan
KAP'ta yayinlanma tarihi ve saati: {published}
https://www.kap.org.tr/tr/Bildirim/{index}
TMS 29 satin alma gucu 31.12.2024
Sunum Para Birimi TL
Dipnot Referansi Cari Donem Onceki Donem
31.12.2024 31.12.2023
Finansal Durum Tablosu (Bilanco)
Nakit ve Nakit Benzerleri 100 100
TOPLAM DONEN VARLIKLAR 3.000 2.000
TOPLAM KISA VADELI YUKUMLULUKLER 1.000 800
TOPLAM VARLIKLAR 5.000 4.000
TOPLAM YUKUMLULUKLER 3.000 2.500
TOPLAM OZKAYNAKLAR 2.000 1.500
Kisa Vadeli Borclanmalar 500 300
Uzun Vadeli Borclanmalarin Kisa Vadeli Kisimlari 200 100
Ticari Alacaklar 400 100
Sunum Para Birimi TL
Dipnot Referansi Cari Donem Onceki Donem
01.01.2024 - 01.01.2023 -
31.12.2024 31.12.2023
Kar veya Zarar Tablosu
Hasilat 1.000 2.000
ESAS FAALIYET KARI (ZARARI) 50 400
DONEM KARI (ZARARI) 100 200
Finansman Giderleri -300 -100
Net Parasal Pozisyon Kazanclari (Kayiplari) 150 100
SURDURULEN FAALIYETLER VERGI ONCESI KARI (ZARARI) 120 250
Sunum Para Birimi TL
Cari Donem Onceki Donem
01.01.2024 - 01.01.2023 -
31.12.2024 31.12.2023
Nakit Akis Tablosu (Dolayli Yontem)
ISLETME FAALIYETLERINDEN NAKIT AKISLARI -500 100
"""


def dataset(settings, text=None):
    raw = pdf(text or report_text())
    source, blocks, _ = accept_kap(raw, 123, COMPANIES["ozatd"], date(2025, 3, 31), settings)
    return Dataset(sources=[source], blocks=blocks)


def numeric_analysis(settings, text=None):
    data = dataset(settings, text)
    facts, _ = extract_financial(data.sources[0], data.blocks)
    return EquityAnalysis(
        run_id="00000000-0000-0000-0000-000000000001",
        company="Synthetic",
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        created_at=datetime.now(UTC),
        sources=data.sources,
        blocks=data.blocks,
        facts=facts,
    )


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1.234,50", "1234.50"),
        ("(12.345)", "-12345"),
        ("-5,25", "-5.25"),
        ("0", "0"),
        ("1.234", "1234"),
    ],
)
def test_turkish_amount(raw, expected):
    assert parse_turkish(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", ["-", "—", "1,234.50", "NaN", "1.2", "(1", "1)"])
def test_ambiguous_amount_rejected(raw):
    with pytest.raises(ValueError):
        parse_turkish(raw)


def test_real_pdf_reader_and_dates_units_signs(settings):
    result = numeric_analysis(settings)
    facts = {(f.concept, f.period_end.year): f for f in result.facts}
    assert facts["operating_cash_flow", 2024].value == -500
    assert facts["revenue", 2024].value == 1000
    assert facts["revenue", 2023].period_start == date(2023, 1, 1)
    assert facts["current_assets", 2024].period_start is None
    assert facts["receivables", 2023].value == 100
    assert all(f.basis_date == date(2024, 12, 31) and f.currency == "TRY" for f in result.facts)
    assert all(
        f.evidence.quote in next(b.text for b in result.blocks if b.id == f.evidence.block_id)
        for f in result.facts
    )


def test_pdf_issuer_id_and_publication_must_match(settings):
    with pytest.raises(ValueError, match="kimliği"):
        accept_kap(
            pdf(report_text().replace("OZATA DENIZCILIK", "ANOTHER COMPANY")),
            123,
            COMPANIES["ozatd"],
            date(2025, 3, 31),
            settings,
        )
    with pytest.raises(ValueError, match="numarası"):
        accept_kap(pdf(report_text()), 456, COMPANIES["ozatd"], date(2025, 3, 31), settings)
    with pytest.raises(ValueError, match="future_publication"):
        accept_kap(pdf(report_text()), 123, COMPANIES["ozatd"], date(2025, 2, 28), settings)
    with pytest.raises(ValueError, match="Birden çok"):
        accept_kap(
            pdf(report_text() + "\nKAP'ta yayinlanma tarihi ve saati: 04.03.2025 10:00:00"),
            123,
            COMPANIES["ozatd"],
            date(2025, 3, 31),
            settings,
        )
    with pytest.raises(ValueError, match="PDF"):
        accept_kap(b"<html>error 200</html>", 123, COMPANIES["ozatd"], date(2025, 3, 31), settings)


def test_frozen_rules_and_domains(settings):
    result = numeric_analysis(settings)
    metrics, findings, coverage, outcome = evaluate(result)
    assert outcome == "dikkat_gerektiriyor"
    assert {"F01", "F03", "F05", "O01"} <= {f.rule_id for f in findings}
    assert next(m for m in metrics if m.id == "revenue_growth").value == Decimal("-0.5")
    assert coverage["financial"] == "available"
    assert next(f for f in findings if f.rule_id == "F04").level == "context"


def test_multiple_financial_ratios_are_one_domain(settings):
    result = numeric_analysis(settings)
    result.facts = [f for f in result.facts if f.concept != "operating_profit"]
    _, findings, _, outcome = evaluate(result)
    assert len([f for f in findings if f.domain == "financial" and f.level == "review"]) >= 2
    assert outcome == "sinirli_isaret"


def test_negative_equity_critical_and_bad_identity_not_risk(settings):
    result = numeric_analysis(settings)
    result.facts = [
        f.model_copy(update={"value": Decimal(-2000)})
        if f.concept == "equity" and f.period_end.year == 2024
        else f
        for f in result.facts
    ]
    _, findings, cov, outcome = evaluate(result)
    assert cov["financial"] == "invalid"
    assert all(f.level == "context" for f in findings)
    assert outcome == "yetersiz_veri"
    result.facts = [
        f.model_copy(update={"value": Decimal(7000)})
        if f.concept == "total_liabilities" and f.period_end.year == 2024
        else f
        for f in result.facts
    ]
    assert evaluate(result)[3] == "dikkat_gerektiriyor"


def test_missing_cells_are_not_zero_and_conflicts_rejected(settings):
    result = numeric_analysis(
        settings,
        report_text().replace(
            "Nakit ve Nakit Benzerleri 100 100", "Nakit ve Nakit Benzerleri - 100"
        ),
    )
    assert not any(f.concept == "cash" and f.period_end.year == 2024 for f in result.facts)
    data = dataset(
        settings,
        report_text().replace("Hasilat 1.000 2.000", "Hasilat 1.000 2.000\nHasilat 9.000 2.000"),
    )
    facts, rejected = extract_financial(data.sources[0], data.blocks)
    assert any(r["reason"] == "conflicting_values" for r in rejected)
    assert not any(f.concept == "revenue" and f.period_end.year == 2024 for f in facts)


def test_interim_comparison_does_not_mix_year_end_receivables(settings):
    result = numeric_analysis(settings)
    for i, fact in enumerate(result.facts):
        if fact.period_start:
            result.facts[i] = fact.model_copy(
                update={"period_end": date(fact.period_end.year, 6, 30)}
            )
    # Newest period is still year-end balance; no mismatched flow ratios are constructed.
    metrics, _, _, _ = evaluate(result)
    assert not any(m.id == "receivable_days_change" for m in metrics)


def test_date_only_is_next_day():
    assert available_at(date(2025, 4, 30)) > cutoff(date(2025, 4, 30))
    assert available_at(date(2025, 4, 30)) <= cutoff(date(2025, 5, 1))
    with pytest.raises(ValueError):
        available_at(datetime(2025, 1, 1))


def test_safe_paths_and_urls(tmp_path):
    with pytest.raises(ValueError):
        local_file(tmp_path, "../private", 100)
    for url in (
        "http://www.kap.org.tr/a",
        "https://www.kap.org.tr.evil.test/a",
        "https://user:pass@kap.org.tr/a",
        "https://kap.org.tr:444/a",
        "https://kap.org.tr/a#x",
    ):
        assert not safe_url(url)
    assert safe_url("https://www.kap.org.tr/tr/api/BildirimPdf/123")


def test_market_csv_future_rows_do_not_change_snapshot():
    raw = b"date,symbol,close,volume\n2025-03-31,OZATD.IS,100,10\n"
    a = read_market_csv(
        raw, "OZATD.IS", "https://example.test/data", "as_traded", date(2025, 3, 31)
    )
    b = read_market_csv(
        raw + b"2026-01-01,OZATD.IS,99999,9999\n",
        "OZATD.IS",
        "https://example.test/data",
        "as_traded",
        date(2025, 3, 31),
    )
    assert a.bars == b.bars and a.sha256 == b.sha256
    with pytest.raises(ValueError, match="sembol"):
        read_market_csv(
            raw, "HATSN.IS", "https://example.test/data", "as_traded", date(2025, 3, 31)
        )


def test_yahoo_trims_before_returning(settings):
    stamp = int(datetime(2025, 3, 31, 15, tzinfo=ISTANBUL).timestamp())
    data = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "OZATD.IS", "currency": "TRY"},
                    "timestamp": [stamp, stamp + 86400],
                    "indicators": {"quote": [{"close": [100, 999], "volume": [1, 1000]}]},
                }
            ],
            "error": None,
        }
    }
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))
    ) as client:
        series = yahoo_series(EquityHTTP(settings, client=client), "OZATD.IS", date(2025, 3, 31))
        assert len(series.bars) == 1 and series.bars[0].close == 100
        assert series.price_basis == "provider_adjusted"


def test_model_quotes_and_boilerplate_not_verdict(settings):
    source = dataset(settings).sources[0]
    block = Block(
        id="b",
        source_id=source.id,
        line_start=1,
        text="Isletmenin surekliliginde onemli belirsizlik durumunda yonetim sorumludur.",
    )
    claim = Claim(
        kind="going_concern",
        evidence=[Locator(block_id="b", quote=block.text)],
        counter_evidence=[],
        relation=None,
    )
    result = TextExtraction(claims=[claim], forecasts=[], holdings=[])
    assert not validate_extraction(result, [block], source, "Synthetic")[0]
    block = block.model_copy(
        update={"text": "Isletmenin surekliligine iliskin onemli bir belirsizlik mevcuttur."}
    )
    result.claims[0].evidence[0].quote = block.text
    assert len(validate_extraction(result, [block], source, "Synthetic")[0]) == 1
    result.claims[0].evidence[0].quote = "A quote that does not exist in the source"
    assert not validate_extraction(result, [block], source, "Synthetic")[0]


def test_pipeline_real_reader_fake_model_and_historical_filter(settings):
    data = dataset(settings)
    future = data.sources[0].model_copy(
        update={"id": "future", "available_at": cutoff(date(2026, 1, 1))}
    )
    data.sources.append(future)
    data.blocks.append(
        Block(id="later", source_id="future", line_start=1, text="FORBIDDEN FUTURE OUTCOME")
    )
    ai = EmptyAI()
    analysis, assessment = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=data,
        codex=ai,
    )
    assert assessment.outcome == "dikkat_gerektiriyor"
    assert not any(s.id == "future" for s in analysis.sources)
    assert all("FORBIDDEN" not in json.dumps(p) for p in ai.packets)
    assert analysis.ai["web_search"] is False
    directory = settings.data_dir / "runs" / analysis.run_id
    assert json.loads((directory / "assessment.json").read_text())[
        "source_analysis_sha256"
    ] == canonical_hash(analysis)
    assert (directory / "report.md").is_file()
    # Same document packets are reused without asking the model again.
    again_ai = EmptyAI()
    second, _ = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=data,
        codex=again_ai,
    )
    assert again_ai.calls == 0 and second.ai["cache_hits"] > 0


def test_empty_data_never_clean(settings):
    a, b = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=Dataset(),
        codex=EmptyAI(),
    )
    assert a.status == "failed" and b.outcome == "yetersiz_veri"


def test_cancelled_run_saved_without_further_model_calls(settings):
    class Interrupted(EmptyAI):
        def ask(self, *args, **kwargs):
            raise KeyboardInterrupt

    analysis, assessment = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=dataset(settings),
        codex=Interrupted(),
    )
    assert analysis.ai["cancelled"] and assessment.outcome == "yetersiz_veri"
    assert set(assessment.coverage.values()) == {"cancelled"}


def test_replay_first_alert_and_event_not_in_model_packets(settings):
    data = dataset(settings)
    store = EquityMemoryStore()
    models = []

    def factory(day):
        ai = EmptyAI()
        models.append(ai)
        return ai

    result = run_replay(
        settings,
        store,
        company_id="ozatd",
        study="pre-2025-spk",
        dataset=data,
        codex_factory=factory,
    )
    assert result["first_indicator_attention"] == "2025-03-31"
    assert result["lead_days"] == 30
    assert len(result["snapshots"]) == 8
    assert result["snapshots"][0]["outcome"] == "yetersiz_veri"
    assert all("event_date" not in p and "lead_days" not in p for ai in models for p in ai.packets)
    assert snapshot_dates("pre-2026-funds")[-1] == date(2026, 9, 16)


def test_bundle_import_has_no_manifest_date_override(settings, tmp_path):
    raw = pdf(report_text())
    (tmp_path / "report.pdf").write_bytes(raw)
    manifest = {"company": "ozatd", "documents": [{"disclosure_id": 123, "file": "report.pdf"}]}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503))) as client:
        result = acquire(
            settings,
            COMPANIES["ozatd"],
            date(2025, 3, 31),
            bundle=tmp_path,
            http=EquityHTTP(settings, client=client),
        )
    assert result.sources[0].published_at.day == 3
    assert result.sources[0].provenance == "manual_kap"
    manifest["documents"][0]["published_at"] = "2024-01-01"
    with pytest.raises(ValueError):
        Bundle.model_validate(manifest)


def test_attachments_require_matching_dated_parent(settings):
    parent = dataset(settings).sources[0]
    oid = "a" * 32
    entry = {"objId": oid, "fileName": "note.pdf", "fileExtension": "pdf"}
    metadata = [
        {
            "disclosure": {
                "disclosureBasic": {"disclosureIndex": 123, "publishDate": "2025.03.03 21:47:48"}
            },
            "attachments": [entry],
        }
    ]
    assert attachment_metadata(json.dumps(metadata).encode(), parent, date(2025, 3, 31)) == [entry]
    metadata[0]["disclosure"]["disclosureBasic"]["publishDate"] = "2026.03.03 21:47:48"
    with pytest.raises(ValueError):
        attachment_metadata(json.dumps(metadata).encode(), parent, date(2025, 3, 31))
    source, blocks, _ = accept_attachment(
        pdf("SYNTHETIC OZATA DENIZCILIK notes"), entry, parent, COMPANIES["ozatd"], settings
    )
    assert source.disclosure_id == parent.disclosure_id and blocks


def test_cli_preserves_enron_and_adds_turkey():
    from bilanco.cli import parser

    p = parser()
    assert (
        p.parse_args(["analyze", "--company", "enron", "--as-of", "2000-03-31"]).company == "enron"
    )
    assert (
        p.parse_args(["analyze", "--company", "OZATD", "--as-of", "2025-03-31"]).company == "ozatd"
    )
    assert (
        p.parse_args(["replay", "--company", "hatsn", "--study", "pre-2025-spk"]).study
        == "pre-2025-spk"
    )


def test_quarter_columns_do_not_replace_cumulative_cash_and_income(settings):
    result = numeric_analysis(settings)
    result.facts += [
        f.model_copy(
            update={"id": f.id + "q", "period_start": date(2024, 10, 1), "value": Decimal(999)}
        )
        for f in result.facts
        if f.concept in {"revenue", "operating_profit", "net_income"} and f.period_end.year == 2024
    ]
    metrics, _, _, _ = evaluate(result)
    assert next(m for m in metrics if m.id == "revenue_growth").value == Decimal("-0.5")
    assert next(m for m in metrics if m.id == "profit_cash_gap").value == 600


def test_mixed_purchasing_power_cannot_produce_alert(settings):
    result = numeric_analysis(settings)
    result.facts = [
        f.model_copy(update={"basis_date": date(2023, 12, 31)}) if f.period_end.year == 2023 else f
        for f in result.facts
    ]
    _, findings, coverage, outcome = evaluate(result)
    assert coverage["financial"] == coverage["operations"] == "invalid"
    assert outcome == "yetersiz_veri" and all(f.level == "context" for f in findings)


def test_future_documents_and_prices_do_not_change_past_indicators(settings):
    from datetime import timedelta

    from bilanco.equity_models import MarketSeries, PriceBar

    result = numeric_analysis(settings)
    days = []
    cursor = result.as_of
    while len(days) < 85:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    days.reverse()

    def series(symbol, benchmark=False):
        bars = [
            PriceBar(
                symbol=symbol,
                day=day,
                close=Decimal(100 if benchmark else 10 + i),
                volume=Decimal(100),
            )
            for i, day in enumerate(days)
        ]
        return MarketSeries(
            symbol=symbol,
            url="https://example.test/" + symbol,
            retrieved_at=datetime.now(UTC),
            sha256=symbol,
            price_basis="as_traded",
            bars=bars,
        )

    result.market = [series("OZATD.IS"), series("XU100.IS", True)]
    before = evaluate(result)
    for s in result.market:
        s.bars.append(
            PriceBar(
                symbol=s.symbol, day=date(2026, 1, 1), close=Decimal(99999), volume=Decimal(999999)
            )
        )
    after = evaluate(result)
    assert before == after
    assert any(f.rule_id == "M01" for f in before[1])


def test_relation_is_one_grounded_transaction_and_negation_rejected(settings):
    from bilanco.assessment_models import EvidenceCheck, RelationDraft

    source = dataset(settings).sources[0]
    company = COMPANIES["ozatd"].name
    role = "Ayşe, Karşı Taraf A şirketinin yöneticisidir."
    txn = company + " Karşı Taraf A şirketinden varlık satın aldı."
    block = Block(id="b", source_id=source.id, line_start=1, text=role + "\n" + txn)
    role_ref = Locator(block_id="b", quote=role)
    txn_ref = Locator(block_id="b", quote=txn)
    yes_role = EvidenceCheck(answer="yes", evidence=[role_ref])
    yes_txn = EvidenceCheck(answer="yes", evidence=[txn_ref])
    unknown = EvidenceCheck(answer="unknown", evidence=[])
    relation = RelationDraft(
        finding_ids=["b"],
        company_name=company,
        counterparty="Karşı Taraf A",
        executive="Ayşe",
        kind="related_transaction",
        transaction_scope="single",
        classification_evidence=[txn_ref],
        executive_link=yes_role,
        transaction=yes_txn,
        same_parties=yes_role,
        financial_effect=unknown,
        business_purpose=unknown,
        controls=unknown,
        control_basis="not_found",
        counter_evidence=[],
    )
    claim = Claim(
        kind="relation", evidence=[role_ref, txn_ref], counter_evidence=[], relation=relation
    )
    extraction = TextExtraction(claims=[claim], forecasts=[], holdings=[])
    assert len(validate_extraction(extraction, [block], source, company)[0]) == 1
    extraction.claims[0].relation.transaction_scope = "multiple"
    assert not validate_extraction(extraction, [block], source, company)[0]
    extraction.claims[0].relation.transaction_scope = "single"
    block.text = role + "\n" + txn + " Karşı Taraf A şirketine borç verdi."
    pooled = block.text.split("\n")[1]
    extraction.claims[0].relation.transaction.evidence = [Locator(block_id="b", quote=pooled)]
    assert not validate_extraction(extraction, [block], source, company)[0]


def test_forecast_requires_exact_amount_and_explicit_period(settings):
    from bilanco.equity_models import Forecast

    source = dataset(settings).sources[0]
    text = "01.01.2025 - 31.12.2025 hasılat tahmini: 10.000 TL, 31.12.2024 satın alma gücü."
    block = Block(id="b", source_id=source.id, line_start=1, text=text)
    ref = Locator(block_id="b", quote=text)
    forecast = Forecast(
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        basis_date=date(2024, 12, 31),
        amount_text="10.000",
        currency="TRY",
        evidence=[ref],
    )
    extraction = TextExtraction(claims=[], forecasts=[forecast], holdings=[])
    assert len(validate_extraction(extraction, [block], source, "Synthetic")[1]) == 1
    extraction.forecasts[0].amount_text = "10"
    assert not validate_extraction(extraction, [block], source, "Synthetic")[1]


def test_cancel_replay_preserves_remaining_dates(settings):
    class Stop(EmptyAI):
        def ask(self, *args, **kwargs):
            raise KeyboardInterrupt

    result = run_replay(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        study="pre-2025-spk",
        dataset=dataset(settings),
        codex_factory=lambda _: Stop(),
    )
    assert result["status"] == "cancelled"
    assert result["remaining_dates"] == ["2025-04-29"]


def test_cli_turkey_does_not_require_sec_contact(settings, monkeypatch, capsys):
    from dataclasses import replace

    from bilanco.cli import main

    monkeypatch.setattr("bilanco.cli.Settings.load", lambda: replace(settings, sec_contact=""))
    store = EquityMemoryStore()
    monkeypatch.setattr("bilanco.cli.Store", lambda _: store)

    def run(*args, **kwargs):
        return run_equity(*args, **kwargs, dataset=dataset(settings), codex=EmptyAI())

    monkeypatch.setattr("bilanco.cli.run_equity", run)
    assert main(["analyze", "--company", "ozatd", "--as-of", "2025-03-31"]) == 3
    assert json.loads(capsys.readouterr().out)["outcome"] == "dikkat_gerektiriyor"


def test_offline_bundle_issues_no_financial_http(settings, tmp_path):
    (tmp_path / "KAP.pdf").write_bytes(pdf(report_text()))
    (tmp_path / "manifest.json").write_text(
        json.dumps({"company": "ozatd", "documents": [{"disclosure_id": 123, "file": "KAP.pdf"}]})
    )
    # Autouse fixture forbids real HTTP. No supplied client is needed in offline mode.
    result = acquire(settings, COMPANIES["ozatd"], date(2025, 3, 31), bundle=tmp_path, offline=True)
    assert len(result.sources) == 1
    assert len(result.issues) == 2 and not result.market


def test_public_acquisition_to_pipeline_and_cache(settings):
    from datetime import timedelta

    raw = pdf(report_text())
    calls = []

    def handler(request):
        calls.append(str(request.url))
        path = request.url.path
        if request.method == "POST":
            criteria = json.loads(request.content)
            assert criteria["toDate"] <= "2025-03-31"
            return httpx.Response(
                200,
                json=[
                    {
                        "stockCodes": "OZATD",
                        "relatedStocks": None,
                        "publishDate": "03.03.2025 21:47:48",
                        "subject": "Finansal Rapor",
                        "disclosureIndex": 123,
                    },
                    {
                        "stockCodes": "OZATD",
                        "publishDate": "01.04.2025 12:00:00",
                        "subject": "Future",
                        "disclosureIndex": 999,
                    },
                ],
            )
        if path.endswith("/BildirimPdf/123"):
            return httpx.Response(200, content=raw)
        if path.endswith("/attachment-detail/123"):
            return httpx.Response(
                200,
                json=[
                    {
                        "disclosure": {
                            "disclosureBasic": {
                                "publishDate": "2025.03.03 21:47:48",
                                "disclosureIndex": 123,
                            }
                        },
                        "attachments": [],
                    }
                ],
            )
        symbol = path.split("/")[-1]
        if symbol in {"OZATD.IS", "XU100.IS"}:
            days = [date(2025, 3, 31) - timedelta(days=100 - i) for i in range(101)]
            return httpx.Response(
                200,
                json={
                    "chart": {
                        "error": None,
                        "result": [
                            {
                                "meta": {"symbol": symbol, "currency": "TRY"},
                                "timestamp": [
                                    int(
                                        datetime.combine(
                                            d, datetime.min.time(), ISTANBUL
                                        ).timestamp()
                                    )
                                    for d in days
                                ],
                                "indicators": {
                                    "quote": [{"close": [100] * 101, "volume": [100] * 101}]
                                },
                            }
                        ],
                    }
                },
            )
        pytest.fail("Unexpected request: " + str(request.url))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        http = EquityHTTP(settings, client=client)
        http.last_request = float("-inf")
        data = acquire(settings, COMPANIES["ozatd"], date(2025, 3, 31), http=http)
        count = len(calls)
        again = acquire(settings, COMPANIES["ozatd"], date(2025, 3, 31), http=http)
        assert len(calls) == count
    assert not data.issues and len(data.sources) == 1 and len(again.sources) == 1
    a, b = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=data,
        codex=EmptyAI(),
    )
    assert a.status == b.status == "complete"
    assert b.outcome == "dikkat_gerektiriyor"
    assert not any("999" in c for c in calls)


def test_spk_day_precision_and_only_relevant_company_section(settings):
    from bilanco.equity_sources import SPK_2025, accept_spk

    raw = pdf(
        "SYNTHETIC SPK TEST\n2025/28 30/04/2025\nc) Ozata Denizcilik (OZATD) pay piyasasinda\nislem yasagi uygulanmasina karar verilmistir.\nd) OTHER COMPANY UNRELATED PENALTY"
    )
    with pytest.raises(ValueError, match="future_publication"):
        accept_spk(raw, SPK_2025, COMPANIES["ozatd"], date(2025, 4, 30), settings)
    source, blocks = accept_spk(raw, SPK_2025, COMPANIES["ozatd"], date(2025, 5, 1), settings)
    assert source.available_at.date() == date(2025, 5, 1)
    assert all("OTHER COMPANY" not in b.text for b in blocks)


def test_replay_acquisition_cancellation_is_recorded(settings, monkeypatch):
    def stop(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("bilanco.equity_replay.acquire", stop)
    result = run_replay(settings, EquityMemoryStore(), company_id="ozatd", study="pre-2025-spk")
    assert result["status"] == "cancelled" and len(result["remaining_dates"]) == 8
    assert result["snapshots"] == []


def test_old_adverse_opinion_not_current_after_new_audit(settings):
    result = numeric_analysis(settings)
    result.facts = []
    old = result.sources[0]
    old_block = Block(
        id="old-audit",
        source_id=old.id,
        line_start=1,
        text="Denetim Sonucu Olumsuz\nOlumsuz Görüş\nSYNTHETIC audit statement.",
    )
    result.blocks.append(old_block)
    result.claims = [
        Claim(
            kind="adverse_opinion",
            evidence=[
                Locator(block_id="old-audit", quote="Olumsuz Görüş\nSYNTHETIC audit statement.")
            ],
            counter_evidence=[],
            relation=None,
        )
    ]
    assert evaluate(result)[3] == "dikkat_gerektiriyor"
    newer = old.model_copy(
        update={
            "id": "new-audit",
            "disclosure_id": 456,
            "published_at": datetime(2025, 3, 10, tzinfo=ISTANBUL),
            "available_at": datetime(2025, 3, 10, tzinfo=ISTANBUL),
        }
    )
    result.sources.append(newer)
    result.blocks.append(
        Block(
            id="new-audit-block", source_id="new-audit", line_start=1, text="Denetim Sonucu Olumlu"
        )
    )
    _, findings, _, outcome = evaluate(result)
    assert outcome == "yetersiz_veri" and findings[0].level == "context"


def test_forecast_uses_latest_admitted_revision(settings):
    from bilanco.equity_models import Forecast

    result = numeric_analysis(settings)
    source = result.sources[0]
    old = source.model_copy(
        update={
            "id": "forecast-old",
            "published_at": datetime(2024, 1, 1, tzinfo=ISTANBUL),
            "available_at": datetime(2024, 1, 1, tzinfo=ISTANBUL),
        }
    )
    newer = old.model_copy(
        update={
            "id": "forecast-new",
            "published_at": datetime(2024, 6, 1, tzinfo=ISTANBUL),
            "available_at": datetime(2024, 6, 1, tzinfo=ISTANBUL),
        }
    )
    result.sources.extend([old, newer])
    for sid in ("forecast-old", "forecast-new"):
        result.blocks.append(
            Block(
                id=sid + "-b",
                source_id=sid,
                line_start=1,
                text="SYNTHETIC source-bound forecast data",
            )
        )
    result.forecasts = [
        Forecast(
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            basis_date=date(2024, 12, 31),
            amount_text=amount,
            currency="TRY",
            evidence=[Locator(block_id=sid + "-b", quote="SYNTHETIC source-bound forecast data")],
        )
        for sid, amount in [("forecast-old", "10.000"), ("forecast-new", "1.000")]
    ]
    metrics, findings, _, _ = evaluate(result)
    assert next(m for m in metrics if m.id == "forecast_achievement").value == 1
    assert not any(f.rule_id == "O02" for f in findings)


def test_bad_market_csv_has_actionable_error():
    with pytest.raises(ValueError, match="tutarı"):
        read_market_csv(
            b"date,symbol,close,volume\n2025-03-31,OZATD.IS,wrong,10\n",
            "OZATD.IS",
            "https://example.test/data",
            "as_traded",
            date(2025, 3, 31),
        )


def test_issuer_alias_requires_quoted_definition(settings):
    from bilanco.assessment_models import EvidenceCheck, RelationDraft
    from bilanco.equity_text import validate_relation

    company = COMPANIES["ozatd"].name
    definition = 'Özata Denizcilik Sanayi ve Ticaret Anonim Şirketi ("Şirket") olarak tanımlanır.'
    role = "Ayşe, Karşı Taraf A şirketinin yöneticisidir."
    txn = "Şirket, Karşı Taraf A şirketinden varlık satın aldı."
    block = Block(id="b", source_id="s", line_start=1, text=definition + "\n" + role + "\n" + txn)

    def ref(text):
        return Locator(block_id="b", quote=text)

    def yes(text):
        return EvidenceCheck(answer="yes", evidence=[ref(text)])

    unknown = EvidenceCheck(answer="unknown", evidence=[])
    relation = RelationDraft(
        finding_ids=["b"],
        company_name="Şirket",
        counterparty="Karşı Taraf A",
        executive="Ayşe",
        kind="related_transaction",
        transaction_scope="single",
        classification_evidence=[ref(definition)],
        executive_link=yes(role),
        transaction=yes(txn),
        same_parties=yes(role),
        financial_effect=unknown,
        business_purpose=unknown,
        controls=unknown,
        control_basis="not_found",
        counter_evidence=[],
    )
    claim = Claim(
        kind="relation", evidence=[ref(role), ref(txn)], counter_evidence=[], relation=relation
    )
    assert validate_relation(claim, {"b": block}, company)
    claim.relation.classification_evidence = []
    assert not validate_relation(claim, {"b": block}, company)


def test_regulatory_only_does_not_claim_audit_or_relation_coverage(settings):
    result = numeric_analysis(settings)
    result.sources = [s.model_copy(update={"kind": "regulatory"}) for s in result.sources]
    result.ai = {"extraction_complete": True}
    _, _, coverage, _ = evaluate(result)
    assert coverage["audit"] == coverage["relations"] == "unavailable"
