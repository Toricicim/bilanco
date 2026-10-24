"""Invented evidence only. The expected outputs do not encode a historical case outcome."""

import json
from datetime import date, datetime
from decimal import Decimal

import pytest
from test_equity import EmptyAI, EquityMemoryStore, dataset, pdf, report_text
from test_equity_review_v2 import healthy_snapshot

from bilanco.equity_document_facts import analyze_documents, financial_history
from bilanco.equity_models import COMPANIES, ISTANBUL, DocumentFact, TextExtraction
from bilanco.equity_pipeline import run_equity
from bilanco.equity_review_trace import investor_review, review_trace
from bilanco.equity_rules import evaluate
from bilanco.equity_signals import signal_checks
from bilanco.equity_sources import acquire
from bilanco.equity_text import validate_extraction
from bilanco.models import Block, Locator

NAME = COMPANIES["ozatd"].name
FUND = "Synthetic Asset Management Example Fund"


def neutral(
    a,
    kind,
    value="100",
    *,
    subject="Proje A",
    sid="neutral",
    published="2025-03-03",
    start=date(2024, 1, 1),
    end=date(2024, 12, 31),
    role="issuer",
    owner=None,
    effective=None,
    code="ABC",
    nominal=True,
    day_basis="unknown",
):
    entity = FUND if role == "related_fund" else NAME
    labels = {
        "proceeds_plan": f"Halka arz fon kullanım planı: {subject} için planlanan tutar {value} TL",
        "proceeds_spent": f"Halka arz fon kullanımı: {subject} için kullanılan tutar {value} TL",
        "contract_owner": f"{subject}: {owner} sözleşmenin tarafıdır.",
        "fund_position": f"Finansal yatırımlar, fon katılma payları {subject}: {value} TL",
        "fund_net_assets": f"{subject} fon toplam değeri {value} TL",
        "fund_redemption_days": f"{subject} iade valörü {value} iş günü",
    }
    line = labels[kind]
    dates = [d.strftime("%d.%m.%Y") for d in (start, end, effective) if d]
    text = f"SYNTHETIC TEST ONLY\n{entity}\n" + " ".join(dates) + "\n"
    text += ("Fon raporu" if role == "related_fund" else "Konsolide olmayan") + "\n"
    text += "Nominal tutarlar\n" if nominal else "TMS 29 satın alma gücü 31.12.2024\n"
    text += line
    source = a.sources[0].model_copy(
        update={
            "id": sid,
            "disclosure_id": 1000 + len(a.sources),
            "available_at": datetime.fromisoformat(published).replace(tzinfo=ISTANBUL),
            "published_at": datetime.fromisoformat(published).replace(tzinfo=ISTANBUL),
            "entity_name": entity,
            "entity_code": code if role == "related_fund" else "OZATD",
            "role": role,
            "kind": "fund_disclosure" if role == "related_fund" else "disclosure",
        }
    )
    a.sources.append(source)
    block = Block(id=sid + "-block", source_id=sid, line_start=1, text=text)
    a.blocks.append(block)
    obj = DocumentFact(
        kind=kind,
        entity_name=entity,
        subject=subject,
        counterparty=owner,
        period_start=start,
        period_end=end,
        effective_date=effective,
        value_text=None if kind == "contract_owner" else value,
        currency=None if kind in {"contract_owner", "fund_redemption_days"} else "TRY",
        scope="fund" if role == "related_fund" else "standalone",
        measurement_basis="nominal" if nominal else "inflation_adjusted",
        basis_date=None if nominal else end,
        statement_type="issuer_statement",
        evidence=[Locator(block_id=block.id, quote=text), Locator(block_id=block.id, quote=line)],
        value_evidence=None if kind == "contract_owner" else Locator(block_id=block.id, quote=line),
        counter_evidence=[],
        day_basis=day_basis,
    )
    a.document_facts.append(obj)
    return obj, block, source


def validate(obj, block, source):
    return validate_extraction(
        TextExtraction(claims=[], forecasts=[], holdings=[], document_facts=[obj]),
        [block],
        source,
        source.entity_name,
        include_document_facts=True,
    )


def test_neutral_amounts_produce_review_without_a_source_admitting_a_problem(settings):
    a = healthy_snapshot(settings)
    neutral(a, "proceeds_plan", "100", sid="plan", published="2024-02-01")
    neutral(a, "proceeds_spent", "25", sid="actual")
    baseline = a.model_copy(deep=True)
    baseline.document_facts = []
    expected_outcome = evaluate(baseline)[-1]
    a.metrics, findings, coverage, old_outcome = evaluate(a)
    assert a.comparisons[0].status == "difference"
    assert next(m.value for m in a.metrics if m.id.startswith("proceeds_ratio_")) == Decimal("0.25")
    found = next(f for f in findings if f.rule_id == "D-proceeds")
    assert found.level == "review" and not found.contributes_to_outcome
    assert old_outcome == expected_outcome
    traces = review_trace(a, findings, signal_checks(a, findings, coverage))
    review = investor_review(findings, traces)
    assert review.status == "inceleme_gerekli" and found.id in review.finding_ids
    assert "dolandırıcılık" in review.message


@pytest.mark.parametrize(
    "mutation",
    [
        "future_publication",
        "future_amount_date",
        "issuer",
        "quote",
        "amount",
        "scale",
        "two_values",
        "legal",
        "no_date",
    ],
)
def test_invented_or_later_evidence_cannot_become_a_comparison(settings, mutation):
    a = healthy_snapshot(settings)
    neutral(a, "proceeds_plan", sid="plan", published="2024-02-01")
    obj, block, source = neutral(a, "proceeds_spent", "25", sid="actual")
    if mutation == "future_publication":
        source.available_at = source.published_at = source.published_at.replace(year=2026)
    elif mutation == "future_amount_date":
        obj.period_end = date(2026, 12, 31)
    elif mutation == "issuer":
        obj.entity_name = "Other Company"
    elif mutation == "quote":
        obj.evidence[0].quote += " fabricated sentence"
    elif mutation == "amount":
        obj.value_text = "24"
    elif mutation in {"scale", "two_values"}:
        line = obj.value_evidence.quote + (" milyon TL" if mutation == "scale" else " 99")
        block.text += "\n" + line
        obj.value_evidence = Locator(block_id=block.id, quote=line)
        obj.evidence.append(obj.value_evidence)
    elif mutation == "legal":
        obj.statement_type = "court_decision"
    else:
        obj.period_end = None
    _, findings, comparisons, _ = analyze_documents(a)
    assert not findings and not any(c.status == "difference" for c in comparisons)


@pytest.mark.parametrize(
    "mutation", ["nine_months", "currency", "scope", "basis", "unknown_basis", "late_plan"]
)
def test_noncomparable_plans_do_not_raise_a_review(settings, mutation):
    a = healthy_snapshot(settings)
    plan, _, _ = neutral(a, "proceeds_plan", sid="plan", published="2024-02-01")
    actual, block, source = neutral(a, "proceeds_spent", "25", sid="actual")
    if mutation == "nine_months":
        # The date must first be grounded, then the different periods still cannot match.
        actual.period_end = date(2024, 9, 30)
        block.text = block.text.replace("31.12.2024", "30.09.2024")
        for ref in actual.evidence:
            ref.quote = ref.quote.replace("31.12.2024", "30.09.2024")
    elif mutation == "currency":
        actual.currency = "USD"
        block.text = block.text.replace("TL", "USD")
        for ref in actual.evidence:
            ref.quote = ref.quote.replace("TL", "USD")
        actual.value_evidence.quote = actual.value_evidence.quote.replace("TL", "USD")
    elif mutation == "scope":
        actual.scope = "unknown"
    elif mutation == "basis":
        actual.basis_date = date(2023, 12, 31)
        block.text += "\n31.12.2023"
        actual.evidence[0].quote = block.text
    elif mutation == "unknown_basis":
        plan.measurement_basis = actual.measurement_basis = "unknown"
    else:
        a.sources[-2].available_at = a.sources[-2].published_at = a.sources[
            -2
        ].published_at.replace(year=2025)
    assert validate(actual, block, source)[-1] == [actual]
    assert not analyze_documents(a)[1]


def test_same_period_plan_is_not_a_problem_when_realization_matches(settings):
    a = healthy_snapshot(settings)
    neutral(a, "proceeds_plan", sid="plan", published="2024-02-01")
    neutral(a, "proceeds_spent", sid="actual")
    assert analyze_documents(a)[2][0].status == "consistent"
    assert not analyze_documents(a)[1]


@pytest.mark.parametrize("same_project", [True, False])
def test_explicit_plan_revision_is_context_only_for_that_project(settings, same_project):
    a = healthy_snapshot(settings)
    neutral(a, "proceeds_plan", sid="plan", published="2024-02-01")
    actual, block, _ = neutral(a, "proceeds_spent", "25", sid="actual")
    quote = ("Proje A" if same_project else "Proje B") + " fon kullanım planı güncellenmiştir."
    block.text += "\n" + quote
    actual.counter_evidence = [Locator(block_id=block.id, quote=quote)]
    _, findings, comparisons, _ = analyze_documents(a)
    assert comparisons[0].status == ("context" if same_project else "difference")
    assert bool(findings) is not same_project


def test_contract_party_difference_is_found_from_neutral_statements(settings):
    a = healthy_snapshot(settings)
    neutral(a, "contract_owner", sid="one", owner="Synthetic Listed Company")
    neutral(a, "contract_owner", sid="two", owner="Synthetic Parent Company")
    _, findings, comparisons, _ = analyze_documents(a)
    assert comparisons[0].status == "difference" and findings[0].rule_id == "D-contract_party"
    assert len(findings[0].evidence) >= 2 and not findings[0].contributes_to_outcome


def test_fund_ratio_uses_dated_fund_source_and_keeps_liquidity_unknown(settings):
    a = healthy_snapshot(settings)
    neutral(a, "fund_position", "90", subject="ABC", sid="position", start=None)
    neutral(a, "fund_net_assets", "100", subject="ABC", sid="fund", role="related_fund", start=None)
    metrics, findings, _, exposures = analyze_documents(a)
    nav = next(m for m in metrics if m.id.startswith("fund_position_nav_"))
    assets = next(m for m in metrics if m.id.startswith("fund_position_assets_"))
    assert nav.value == Decimal("0.9") and assets.value == Decimal("0.018")
    assert "NOT verified ownership" in nav.formula
    assert exposures[0].redemption_days is None and exposures[0].missing_inputs
    assert exposures[0].related_source_ids == ["fund"]
    assert not findings


@pytest.mark.parametrize(
    "mutation",
    [
        "future_fund",
        "wrong_code",
        "unknown_basis",
        "wrong_date",
        "wrong_role",
        "different_currency",
    ],
)
def test_fund_comparison_cannot_borrow_current_or_unrelated_data(settings, mutation):
    a = healthy_snapshot(settings)
    pos, _, _ = neutral(a, "fund_position", "90", subject="ABC", sid="position", start=None)
    total, _, source = neutral(
        a, "fund_net_assets", "100", subject="ABC", sid="fund", role="related_fund", start=None
    )
    if mutation == "future_fund":
        source.available_at = source.published_at = source.available_at.replace(year=2026)
    elif mutation == "wrong_code":
        source.entity_code = "XYZ"
    elif mutation == "unknown_basis":
        pos.measurement_basis = total.measurement_basis = "unknown"
    elif mutation == "wrong_date":
        total.period_end = date(2024, 12, 30)
    elif mutation == "wrong_role":
        source.role = "issuer"
    else:
        total.currency = "USD"
    assert not any(m.id.startswith("fund_position_nav_") for m in analyze_documents(a)[0])


def test_missing_fund_document_does_not_turn_investment_into_cash(settings):
    a = healthy_snapshot(settings)
    neutral(a, "fund_position", "90", subject="ABC", sid="position", start=None)
    metrics, findings, _, exposures = analyze_documents(a)
    assert not findings and not any(m.id.startswith("fund_position_nav_") for m in metrics)
    assert next(m.value for m in metrics if m.id.startswith("fund_position_assets_")) == Decimal(
        "0.018"
    )
    assert exposures and exposures[0].missing_inputs and not exposures[0].related_source_ids


def test_redemption_keeps_business_day_basis_and_requires_effective_date(settings):
    a = healthy_snapshot(settings)
    neutral(a, "fund_position", "90", subject="ABC", sid="position", start=None)
    neutral(
        a,
        "fund_redemption_days",
        "3",
        subject="ABC",
        sid="fund",
        role="related_fund",
        start=None,
        effective=date(2024, 12, 31),
        day_basis="business",
    )
    exposure = analyze_documents(a)[3][0]
    assert exposure.redemption_days == 3 and exposure.redemption_day_basis == "business"
    a.document_facts[-1].day_basis = "unknown"
    assert analyze_documents(a)[3][0].redemption_days is None


def test_validation_retains_rejection_reason_and_original_candidate(settings):
    a = healthy_snapshot(settings)
    obj, block, source = neutral(a, "proceeds_spent", "25")
    obj.value_text = "250"
    *_, rejected, accepted = validate(obj, block, source)
    assert not accepted and rejected[0]["reason"] == "document_fact_value_not_grounded"
    assert rejected[0]["candidate"]["value_text"] == "250"


def test_value_span_can_be_a_grounded_subset_of_a_larger_evidence_quote(settings):
    a = healthy_snapshot(settings)
    obj, block, source = neutral(a, "proceeds_spent", "25")
    obj.evidence = obj.evidence[:1]
    assert validate(obj, block, source)[-1] == [obj]
    # A number elsewhere in the same block cannot silently replace the quoted row.
    other = "Başka proje için kullanılan tutar 250 TL"
    block.text += "\n" + other
    obj.value_text = "250"
    obj.value_evidence = Locator(block_id=block.id, quote=other)
    *_, rejected, accepted = validate(obj, block, source)
    assert not accepted and rejected[0]["reason"] == "document_fact_value_span_invalid"


@pytest.mark.parametrize(
    "kind,subject,other",
    [("fund_position", "ABC", "XYZ"), ("proceeds_spent", "Proje A", "Proje B")],
)
def test_amount_cannot_be_taken_from_another_fund_or_project_row(settings, kind, subject, other):
    a = healthy_snapshot(settings)
    obj, block, source = neutral(a, kind, "25", subject=subject)
    quote = obj.value_evidence.quote.replace(subject, other)
    block.text += "\n" + quote
    obj.evidence.append(Locator(block_id=block.id, quote=quote))
    obj.value_evidence = Locator(block_id=block.id, quote=quote)
    *_, rejected, accepted = validate(obj, block, source)
    assert not accepted and rejected[0]["reason"] == "document_fact_value_subject_mismatch"


@pytest.mark.parametrize("prior_cell", ["-", "40"])
def test_comparative_fund_row_binds_value_to_ordered_header_not_bullets(settings, prior_cell):
    a = healthy_snapshot(settings)
    obj, block, source = neutral(a, "fund_position", "90", subject="ABC", start=None)
    line = f"- ABC Yatırım Fonu 90 {prior_cell}"
    table = "Finansal yatırımlar 31.12.2024 31.12.2023\n" + line
    block.text += "\n" + table
    obj.evidence.append(Locator(block_id=block.id, quote=table))
    obj.value_evidence = Locator(block_id=block.id, quote=line)
    assert validate(obj, block, source)[-1] == [obj]
    obj.period_end = date(2023, 12, 31)
    *_, rejected, accepted = validate(obj, block, source)
    assert not accepted and rejected[0]["reason"] == "document_fact_value_period_mismatch"


def test_two_periods_are_not_double_counted_as_extra_quarters(settings):
    a = healthy_snapshot(settings)
    original = financial_history(a)
    a.facts += [f.model_copy() for f in a.facts]
    repeated = financial_history(a)
    assert len(original) == len(repeated) == 2
    assert all(p.cash_profit == 1 or p.cash_profit == Decimal("0.5") for p in repeated)


def test_pipeline_exports_review_comparisons_coverage_and_history(settings):
    text = report_text() + "\n" + NAME + "\n"
    store = EquityMemoryStore()
    analysis, assessment = run_equity(
        settings,
        store,
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=dataset(settings, text),
        codex=EmptyAI(),
    )
    directory = settings.data_dir / "runs" / analysis.run_id
    saved = json.loads((directory / "assessment.json").read_text())
    assert saved["schema_version"] == "tr-assessment-1.3"
    assert len(saved["check_traces"]) == 18 and saved["investor_review"]
    assert analysis.financial_history and assessment.investor_review
    assert "Yatırım öncesi inceleme" in (directory / "report.md").read_text()


def test_neutral_comparison_survives_actual_pipeline_validation_and_json(settings):
    from bilanco.equity_sources import Dataset

    a = healthy_snapshot(settings)
    neutral(a, "proceeds_plan", "100", sid="plan", published="2024-02-01")
    neutral(a, "proceeds_spent", "25", sid="actual")

    class NeutralAI(EmptyAI):
        def ask(self, task, packet, schema, **kwargs):
            self.calls += 1
            assert kwargs["discovery"] is False
            assert "target_event_observed" not in packet
            ids = {b["id"] for b in packet["blocks"]}
            return TextExtraction(
                claims=[],
                forecasts=[],
                holdings=[],
                document_facts=[
                    o for o in a.document_facts if all(r.block_id in ids for r in o.evidence)
                ],
            )

    result, checked = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=a.as_of,
        dataset=Dataset(sources=a.sources, blocks=a.blocks, market=a.market),
        codex=NeutralAI(),
    )
    assert len(result.document_facts) == 2 and result.comparisons[0].status == "difference"
    assert checked.investor_review.status == "inceleme_gerekli"
    saved = json.loads((settings.data_dir / "runs" / result.run_id / "analysis.json").read_text())
    assert saved["comparisons"][0]["input_ids"] and saved["financial_history"]
    assert all(ref in saved["document_fact_index"] for ref in saved["comparisons"][0]["input_ids"])


def test_related_fund_bundle_requires_primary_link_and_own_publication_proof(settings, tmp_path):
    root = tmp_path / "bundle"
    root.mkdir()
    issuer = report_text() + f"\nFinansal yatirimlar ABC {FUND} 90 TL\n"
    fund = report_text(index=456).replace("OZATA DENIZCILIK SANAYI VE TICARET A.S.", FUND)
    (root / "issuer.pdf").write_bytes(pdf(issuer))
    (root / "fund.pdf").write_bytes(pdf(fund))
    manifest = {
        "company": "ozatd",
        "documents": [{"disclosure_id": 123, "file": "issuer.pdf"}],
        "related_documents": [
            {"disclosure_id": 456, "file": "fund.pdf", "fund_code": "ABC", "fund_name": FUND}
        ],
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    data = acquire(settings, COMPANIES["ozatd"], date(2025, 3, 31), bundle=root, offline=True)
    assert not data.rejected and data.sources[-1].role == "related_fund"
    assert data.sources[-1].entity_code == "ABC" and data.sources[-1].kind == "fund_disclosure"
    (root / "fund.pdf").write_bytes(pdf(fund.replace("03.03.2025", "03.04.2025")))
    data = acquire(settings, COMPANIES["ozatd"], date(2025, 3, 31), bundle=root, offline=True)
    assert len(data.sources) == 1 and "future_publication" in data.rejected[0]["reason"]
    manifest["related_documents"][0]["fund_code"] = "XYZ"
    (root / "manifest.json").write_text(json.dumps(manifest))
    data = acquire(settings, COMPANIES["ozatd"], date(2025, 3, 31), bundle=root, offline=True)
    assert len(data.sources) == 1 and "related_fund_link_unverified" in data.rejected[0]["reason"]
