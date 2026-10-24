"""Synthetic counterexamples: facts recovered, normal dealings not converted to fraud alarms."""

from datetime import date
from decimal import Decimal

import httpx
import pytest
from test_equity import (
    EmptyAI,
    EquityMemoryStore,
    dataset,
    numeric_analysis,
    pdf,
    report_text,
)

from bilanco.ai import AIError
from bilanco.assessment_models import EvidenceCheck
from bilanco.equity_models import COMPANIES, CorporateObservation, TextExtraction
from bilanco.equity_pipeline import run_equity
from bilanco.equity_rules import evaluate
from bilanco.equity_sources import EquityHTTP, acquire, fold
from bilanco.equity_tables import dates_in, extract_financial, report_context
from bilanco.equity_text import extract_packet, validate_extraction
from bilanco.models import Block, Locator


def test_unicode_apostrophe_preserves_word_boundary():
    assert fold("Tersanecilik’in") == fold("Tersanecilik'in")
    assert fold("Tersanecilik’in") != fold("Tersanecilikin")


def test_rejected_candidate_and_specific_reason_are_retained(settings):
    data = dataset(settings)
    # Names in a quotation do not prove that the quotation belongs to the packet.
    obj = observation("guarantee")
    obj.evidence = [Locator(block_id="not-supplied", quote="invented statement not in packet")]
    result = TextExtraction(claims=[], forecasts=[], holdings=[], observations=[obj])
    *_, rejected, accepted = validate_extraction(
        result, data.blocks, data.sources[0], COMPANIES["ozatd"].name, include_observations=True
    )
    assert not accepted
    assert rejected[0]["reason"] == "observation_references_invalid"
    assert rejected[0]["candidate"]["evidence"][0]["block_id"] == "not-supplied"
    assert rejected[0]["source_id"] == data.sources[0].id


def observation(kind="guarantee", controls="unknown", phrase=None):
    company = COMPANIES["ozatd"].name
    text = f"SYNTHETIC TEST. {company}\n31.12.2024 satın alma gücü, tutarlar TL.\n"
    text += {
        "guarantee": "Ana ortak lehine teminat toplamı 100 TL.",
        "related_purchase": "İlişkili taraftan alışlar: Ana ortak 100 TL.",
        "asset_transaction": "Ana ortak şirketinden varlık satın alındı, 100 TL.",
    }[kind]
    if phrase:
        text += "\n" + phrase
    ref = Locator(block_id="obs", quote=text)
    return CorporateObservation(
        kind=kind,
        company_name=company,
        counterparty="Ana ortak",
        person=None,
        period_end=date(2024, 12, 31),
        effective_date=None,
        amount_text="100",
        currency="TRY",
        basis_date=date(2024, 12, 31),
        amount_evidence=Locator(block_id="obs", quote=text.splitlines()[2]),
        evidence=[ref],
        counter_evidence=[ref] if controls == "yes" else [],
        controls=EvidenceCheck(answer=controls, evidence=[ref] if controls != "unknown" else []),
        business_purpose=EvidenceCheck(answer="unknown", evidence=[]),
    )


def add_observation(result, obj):
    result.blocks.append(
        Block(id="obs", source_id=result.sources[0].id, line_start=1, text=obj.evidence[0].quote)
    )
    result.observations.append(obj)


@pytest.mark.parametrize("kind", ["guarantee", "related_purchase", "asset_transaction"])
@pytest.mark.parametrize("control", ["unknown", "yes"])
def test_normal_or_unknown_controls_are_not_automatic_alarm(settings, kind, control):
    result = numeric_analysis(settings)
    obj = observation(
        kind,
        control,
        "Ana ortak işlemi bağımsız değerleme ve yönetim kurulu onayı ile yapılmıştır."
        if control == "yes"
        else None,
    )
    add_observation(result, obj)
    extraction = TextExtraction(claims=[], forecasts=[], holdings=[], observations=[obj])
    validated = validate_extraction(
        extraction,
        result.blocks,
        result.sources[0],
        COMPANIES["ozatd"].name,
        include_observations=True,
    )
    assert validated[4] == [obj] and not validated[3]
    before = evaluate(result.model_copy(update={"observations": []}))[3]
    _, findings, _, after = evaluate(result)
    obs = next(f for f in findings if f.rule_id == "R-OBS")
    assert obs.level == "context" and not obs.contributes_to_outcome
    assert before == after
    assert obs.counter_evidence == obj.counter_evidence
    if control == "unknown":
        assert any("kontrol yokluğu çıkarılmadı" in x for x in obs.unknowns)


def test_explicit_control_gap_is_separate_review_not_unvalidated_company_vote(settings):
    result = numeric_analysis(settings)
    obj = observation(controls="no", phrase="Ana ortak işlemi için onay alınmadı.")
    add_observation(result, obj)
    validated = validate_extraction(
        TextExtraction(claims=[], forecasts=[], holdings=[], observations=[obj]),
        result.blocks,
        result.sources[0],
        COMPANIES["ozatd"].name,
        include_observations=True,
    )
    assert validated[4] == [obj]
    _, findings, _, _ = evaluate(result)
    candidate = next(f for f in findings if f.rule_id == "R02")
    assert candidate.level == "review" and not candidate.contributes_to_outcome


@pytest.mark.parametrize(
    "phrase",
    [
        "Ana ortak hakkında onay bilgisi bulunamadı.",
        "Ana ortak işlemi için onay alınmadı iddiası doğru değildir.",
    ],
)
def test_unknown_or_denied_allegation_cannot_become_control_absence(settings, phrase):
    result = numeric_analysis(settings)
    obj = observation(controls="no", phrase=phrase)
    add_observation(result, obj)
    output = validate_extraction(
        TextExtraction(claims=[], forecasts=[], holdings=[], observations=[obj]),
        result.blocks,
        result.sources[0],
        COMPANIES["ozatd"].name,
        include_observations=True,
    )
    assert not output[4] and output[3]


def test_guarantee_amount_is_not_cash_debt_or_loss(settings):
    result = numeric_analysis(settings)
    obj = observation()
    add_observation(result, obj)
    metrics, findings, _, _ = evaluate(result)
    exposure = next(m for m in metrics if m.id.startswith("exposure_"))
    assert exposure.value == Decimal("0.05") and exposure.formula == "disclosed_guarantee / equity"
    assert not any(f.level != "context" and f.domain == "relations" for f in findings)
    # Incompatible nominal versus purchasing-power money must not produce a ratio.
    result.observations[0].basis_date = None
    assert not any(m.id.startswith("exposure_") for m in evaluate(result)[0])


def test_short_and_long_investments_do_not_conflict_or_become_cash(settings):
    text = report_text().replace(
        "Nakit ve Nakit Benzerleri 100 100",
        """DONEN VARLIKLAR
Nakit ve Nakit Benzerleri 100 100
Finansal Yatirimlar 900 -
DURAN VARLIKLAR
Finansal Yatirimlar 20 10""",
    )
    data = dataset(settings, text)
    facts, rejected = extract_financial(data.sources[0], data.blocks)
    current = [
        f for f in facts if f.concept == "financial_investments" and f.period_end.year == 2024
    ]
    assert {(f.maturity, f.value) for f in current} == {
        ("current", Decimal(900)),
        ("noncurrent", Decimal(20)),
    }
    assert any(r["reason"] == "missing_cell" for r in rejected)
    result = numeric_analysis(settings, text)
    metrics, findings, _, _ = evaluate(result)
    assert (
        next(m for m in metrics if m.id == "cash_short_financial_debt").value == Decimal(100) / 700
    )
    sensitivity = next(
        m for m in metrics if m.id == "cash_plus_current_investments_debt_sensitivity"
    )
    assert sensitivity.value == Decimal(1000) / 700 and "UNVERIFIED" in sensitivity.formula
    assert next(f for f in findings if f.rule_id == "F03").counter_evidence


def test_blank_column_is_not_guessed_even_with_maturity(settings):
    text = report_text().replace(
        "Nakit ve Nakit Benzerleri 100 100", "DONEN VARLIKLAR\nFinansal Yatirimlar 900"
    )
    data = dataset(settings, text)
    facts, rejected = extract_financial(data.sources[0], data.blocks)
    assert not any(f.concept == "financial_investments" for f in facts)
    assert any(r["reason"] == "ambiguous_columns" for r in rejected)


def test_linked_inflation_statement_requires_same_scope_and_basis(settings):
    text = (
        report_text()
        .replace("31.12.2024 DONEMI", "31.12.2024")
        .replace("TMS 29 satin alma gucu 31.12.2024", "")
    )
    data = dataset(settings, text)
    source = data.sources[0]
    assert source.kind == "financial"
    assert extract_financial(source, data.blocks)[1][0]["reason"] == "inflation_basis_unverified"
    context = Block(
        id="linked",
        source_id="sibling",
        line_start=1,
        text="""Finansal Tablo Türü Solo Solo
(Tutarlar Türk Lirası'nın 31 Aralık 2024 tarihi itibarıyla satın alma gücü esasına göre ifade edilmiştir.)
TMS 29 konsolide finansal tablolar da dahil genel politikadır.""",
    )
    scope, basis, _, _ = report_context([context])
    assert scope == "standalone" and basis == date(2024, 12, 31)
    facts, rejected = extract_financial(source, data.blocks, linked_blocks=[context])
    assert facts and not rejected and all(f.basis_evidence for f in facts)
    context.text = context.text.replace("31 Aralık 2024", "31 Aralık 2023")
    assert not extract_financial(source, data.blocks, linked_blocks=[context])[0]


def test_month_name_attachment_preserves_missing_cell_and_financial_period(settings):
    data = dataset(settings)
    source = data.sources[0].model_copy(update={"kind": "financial_attachment"})
    block = Block(
        id="attachment",
        source_id=source.id,
        line_start=1,
        text="""SYNTHETIC
31 ARALIK 2024 TARİHİ İTİBARIYLA FİNANSAL DURUM TABLOSU
(Tutarlar Türk Lirası'nın 31 Aralık 2024 tarihi itibarıyla satın alma gücü esasına göre TL olarak ifade edilmiştir.)
Dipnot Referansi
Finansal Tablo Türü Solo Solo
Dönem 31 Aralık 2024 31 Aralık 2023
DONEN VARLIKLAR
Finansal Yatırımlar 6 900 -
DURAN VARLIKLAR
Finansal Yatırımlar 6 20 10
1 OCAK - 31 ARALIK 2024 HESAP DÖNEMİNE AİT NAKİT AKIŞ TABLOSU
Dipnot Referansi
1 Ocak- 1 Ocak-
Dönem
31 Aralık 2024 31 Aralık 2023
İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI (500) 100
""",
    )
    facts, _ = extract_financial(source, [block])
    ocf = next(f for f in facts if f.concept == "operating_cash_flow" and f.period_end.year == 2024)
    assert ocf.value == -500 and ocf.period_start == date(2024, 1, 1)
    assert any(
        f.concept == "financial_investments" and f.maturity == "current" and f.value == 900
        for f in facts
    )
    assert dates_in("30 Eylül 2024 ve 31.12.2024") == [date(2024, 9, 30), date(2024, 12, 31)]


def test_conflicting_authenticated_appendix_is_not_silently_preferred(settings):
    result = numeric_analysis(settings)
    parent = result.sources[0]
    appendix = parent.model_copy(update={"id": "appendix", "kind": "financial_attachment"})
    result.sources.append(appendix)
    f = next(f for f in result.facts if f.concept == "net_income" and f.period_end.year == 2024)
    result.facts.append(
        f.model_copy(update={"id": "conflict", "source_id": appendix.id, "value": f.value + 1})
    )
    _, findings, coverage, outcome = evaluate(result)
    assert coverage["financial"] == "invalid" and outcome == "yetersiz_veri"
    assert all(f.level == "context" for f in findings)


def test_scan_and_validation_coverage_are_separate_and_failures_have_manifest(settings):
    class Fails(EmptyAI):
        def ask(self, *args, **kwargs):
            raise AIError("Synthetic exhausted budget")

    a, b = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=dataset(settings),
        codex=Fails(),
    )
    assert a.ai["packets_planned"] >= 1 and a.ai["packets_processed"] == 0
    assert not a.ai["scan_complete"] and not a.ai["extraction_complete"]
    assert a.ai["packet_manifest"][0]["status"] == "failed"
    assert b.coverage["relations"] == "unavailable"


def test_one_rejected_candidate_does_not_erase_scanned_audit(settings):
    class Bad(EmptyAI):
        def ask(self, *args, **kwargs):
            obj = observation()
            return TextExtraction(claims=[], forecasts=[], holdings=[], observations=[obj])

    a, b = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=dataset(settings),
        codex=Bad(),
    )
    assert a.ai["scan_complete"] and not a.ai["extraction_complete"]
    assert b.coverage["audit"] == "text_scanned_with_rejections"
    assert a.rejected[0]["candidate"]


def test_new_prompt_does_not_reuse_old_contract_cache(settings):
    class Recorder(EmptyAI):
        def ask(self, task, packet, schema, **kwargs):
            assert task == "tr_equity_evidence_v2" and packet["schema_sha256"]
            assert "transaction_scope" in packet["relation_contract"]
            return super().ask(task, packet, schema, **kwargs)

    data = dataset(settings)
    ai = Recorder()
    assert not extract_packet(ai, settings, data.sources[0], data.blocks, COMPANIES["ozatd"].name)[
        -1
    ]
    assert extract_packet(ai, settings, data.sources[0], data.blocks, COMPANIES["ozatd"].name)[-1]
    assert ai.calls == 1


def test_failed_attachment_does_not_skip_next_sibling(settings):
    first, second = "a" * 32, "b" * 32
    entries = [
        {"objId": oid, "fileName": oid + ".pdf", "fileExtension": "pdf"} for oid in [first, second]
    ]
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.method == "POST":
            return httpx.Response(
                200,
                json=[
                    {
                        "stockCodes": "OZATD",
                        "publishDate": "03.03.2025 21:47:48",
                        "subject": "Finansal Rapor",
                        "disclosureIndex": 123,
                    }
                ],
            )
        if request.url.path.endswith("BildirimPdf/123"):
            return httpx.Response(200, content=pdf(report_text()))
        if "attachment-detail" in request.url.path:
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
                        "attachments": entries,
                    }
                ],
            )
        if request.url.path.endswith(first):
            return httpx.Response(200, content=b"not PDF")
        if request.url.path.endswith(second):
            return httpx.Response(200, content=pdf("SYNTHETIC OZATA DENIZCILIK second exhibit"))
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = acquire(
            settings,
            COMPANIES["ozatd"],
            date(2025, 3, 31),
            http=EquityHTTP(settings, client=client),
        )
    assert any(s.id.startswith("kap-123-" + second) for s in result.sources)
    assert any(r.get("obj_id") == first and r.get("stage") == "attachment" for r in result.rejected)


def test_no_negative_finding_with_unread_text_is_not_clear_company(settings):
    result = numeric_analysis(settings)
    # Positive cash flow and steady operations remove the known numerical triggers.
    result.facts = [
        f.model_copy(update={"value": Decimal(100)}) if f.concept == "operating_cash_flow" else f
        for f in result.facts
    ]
    result.facts = [f for f in result.facts if f.concept not in {"operating_profit", "receivables"}]
    result.ai = {
        "source_coverage": {result.sources[0].id: {"planned": 3, "processed": 1, "failed": 2}}
    }
    _, findings, _, outcome = evaluate(result)
    assert all(f.level == "context" for f in findings) and outcome == "yetersiz_veri"


def healthy_snapshot(settings):
    from datetime import timedelta

    from bilanco.equity_models import MarketSeries, PriceBar

    result = numeric_analysis(settings)
    for fact in result.facts:
        if fact.concept == "operating_cash_flow":
            fact.value = Decimal(100)
        if fact.concept == "operating_profit":
            fact.value = Decimal(400)
        if fact.concept == "receivables" and fact.period_end.year == 2024:
            fact.value = Decimal(40)
    result.market = [
        MarketSeries(
            symbol=symbol,
            url="https://synthetic.invalid/flat",
            retrieved_at=result.created_at,
            sha256=symbol,
            price_basis="as_traded",
            bars=[
                PriceBar(
                    symbol=symbol,
                    day=result.as_of - timedelta(days=i),
                    close=Decimal(100),
                    volume=Decimal(100),
                )
                for i in range(85, -1, -1)
            ],
        )
        for symbol in ("OZATD.IS", "XU100.IS")
    ]
    result.ai = {
        "acquisition_complete": True,
        "source_coverage": {
            result.sources[0].id: {
                "planned": 1,
                "processed": 1,
                "failed": 0,
                "rejections": 0,
                "read_issues": [],
            }
        },
    }
    return result


@pytest.mark.parametrize("gap", ["acquisition", "packet", "rejection", "unreadable_page"])
def test_healthy_fully_checked_baseline_and_missing_coverage_are_distinct(settings, gap):
    result = healthy_snapshot(settings)
    assert evaluate(result)[3] == "belirgin_isaret_yok"
    entry = result.ai["source_coverage"][result.sources[0].id]
    if gap == "acquisition":
        result.ai["acquisition_complete"] = False
    elif gap == "packet":
        entry["planned"], entry["failed"] = 2, 1
    elif gap == "rejection":
        entry["rejections"] = 1
    else:
        entry["read_issues"] = ["Synthetic unread page"]
    assert evaluate(result)[3] == "yetersiz_veri"


def test_ordinary_related_transaction_cannot_promote_healthy_snapshot(settings):
    result = healthy_snapshot(settings)
    obj = observation(
        "related_purchase", "yes", "Ana ortak işlemi için bağımsız değerleme ve onay vardır."
    )
    add_observation(result, obj)
    assert evaluate(result)[3] == "belirgin_isaret_yok"
    obj.controls = EvidenceCheck(answer="unknown", evidence=[])
    assert (
        evaluate(result)[3] == "belirgin_isaret_yok"
    )  # no assertion of safety or lack of controls


def test_four_flow_columns_in_one_header_line_are_not_dropped():
    from bilanco.equity_tables import periods

    result = periods(
        "01.01.2024 - 30.09.2024 01.01.2023 - 30.09.2023 01.07.2024 - 30.09.2024 01.07.2023 - 30.09.2023",
        True,
    )
    assert result == [
        (date(2024, 1, 1), date(2024, 9, 30)),
        (date(2023, 1, 1), date(2023, 9, 30)),
        (date(2024, 7, 1), date(2024, 9, 30)),
        (date(2023, 7, 1), date(2023, 9, 30)),
    ]


def test_attachment_for_another_reporting_entity_cannot_fill_issuer_numbers(settings):
    data = dataset(settings)
    wrong = Block(
        id="wrong-entity",
        source_id="appendix",
        line_start=1,
        text="""OTHER REPORTING ENTITY
31 ARALIK 2024 TARİHİ İTİBARIYLA FİNANSAL DURUM TABLOSU
(Tutarlar Türk Lirası'nın 31 Aralık 2024 tarihi itibarıyla satın alma gücü esasına göre TL olarak ifade edilmiştir.)
Finansal Tablo Türü Solo Solo
Dönem 31 Aralık 2024 31 Aralık 2023
DONEN VARLIKLAR
Nakit ve Nakit Benzerleri 900 100
"""
        + "Context " * 120
        + "\nOZATA DENIZCILIK is a counterparty, not this report's issuer.",
    )
    source = data.sources[0].model_copy(update={"kind": "financial_attachment", "id": "appendix"})
    assert not extract_financial(source, [wrong], issuer_identity="ozata denizcilik")[0]


def test_abbreviated_issuer_and_missing_executive_preserve_context_not_conflict(settings):
    from bilanco.assessment_models import RelationDraft
    from bilanco.equity_models import Claim

    data = dataset(settings)
    company = "ÖZATA DENİZCİLİK SAN.VE TİC.A.Ş."
    quote = company + " Karşı Taraf A şirketindeki sahiplik yapısını açıklamıştır."
    block = Block(id="role-context", source_id=data.sources[0].id, line_start=1, text=quote)
    ref = Locator(block_id=block.id, quote=quote)
    unknown = EvidenceCheck(answer="unknown", evidence=[])
    relation = RelationDraft(
        finding_ids=[block.id],
        company_name=company,
        counterparty="Karşı Taraf A",
        executive="unknown",
        kind="ownership",
        classification_evidence=[ref],
        executive_link=unknown,
        transaction=unknown,
        same_parties=unknown,
        financial_effect=unknown,
        business_purpose=unknown,
        controls=unknown,
        control_basis="not_found",
        counter_evidence=[],
    )
    draft = TextExtraction(
        claims=[Claim(kind="relation", evidence=[ref], counter_evidence=[], relation=relation)],
        forecasts=[],
        holdings=[],
    )
    claims, _, _, rejected = validate_extraction(
        draft, [block], data.sources[0], COMPANIES["ozatd"].name
    )
    assert len(claims) == 1 and claims[0].relation.executive == "" and not rejected
    # Incomplete executive identities can never complete an executive-conflict chain.
    relation.executive_link = EvidenceCheck(answer="yes", evidence=[ref])
    assert not validate_extraction(draft, [block], data.sources[0], COMPANIES["ozatd"].name)[0]


def test_misspelled_short_name_cannot_be_merged_by_similarity(settings):
    obj = observation()
    obj.counterparty = "Ana ortak A2"
    data = dataset(settings)
    block = Block(id="obs", source_id=data.sources[0].id, line_start=1, text=obj.evidence[0].quote)
    result = validate_extraction(
        TextExtraction(claims=[], forecasts=[], holdings=[], observations=[obj]),
        [block],
        data.sources[0],
        COMPANIES["ozatd"].name,
        include_observations=True,
    )
    assert not result[4] and result[3][0]["reason"] == "observation_counterparty_not_grounded"


def test_wrapped_four_column_header_keeps_cumulative_and_quarter_separate():
    from bilanco.equity_tables import periods

    header = """Dipnot Referansi 01.01.2024 - 01.01.2023 -
01.07.2024 - 01.07.2023 -
30.09.2024 30.09.2023
30.09.2024 30.09.2023"""
    assert periods(header, True) == [
        (date(2024, 1, 1), date(2024, 9, 30)),
        (date(2023, 1, 1), date(2023, 9, 30)),
        (date(2024, 7, 1), date(2024, 9, 30)),
        (date(2023, 7, 1), date(2023, 9, 30)),
    ]


def test_conflicting_control_drafts_are_not_silently_deduplicated(settings):
    result = healthy_snapshot(settings)
    obj = observation("asset_transaction", "yes", "Ana ortak işlemi için değerleme ve onay vardır.")
    add_observation(result, obj)
    second = obj.model_copy(update={"controls": EvidenceCheck(answer="unknown", evidence=[])})
    result.observations.append(second)
    _, findings, _, outcome = evaluate(result)
    related = [f for f in findings if f.rule_id == "R-OBS"]
    assert len(related) == 2
    assert sum(any("kontrol yokluğu" in text for text in f.unknowns) for f in related) == 1
    assert outcome == "belirgin_isaret_yok"
