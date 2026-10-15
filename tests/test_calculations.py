from decimal import Decimal

from conftest import synthetic_filing

from bilanco.calculations import calculate
from bilanco.config import AS_OF
from bilanco.documents import extract_facts, read_document


def test_profit_cash_divergence_is_not_negative_cash_claim(source):
    blocks, _ = read_document(source, synthetic_filing(profit="40", operating="40"))
    facts, _ = extract_facts(blocks, AS_OF)
    metrics, findings, _ = calculate(facts)
    finding = next(f for f in findings if f.id == "cash_profit_divergence_1999")
    assert finding.status == "signal"
    assert (
        next(f for f in facts if f.concept == "operating_cash_flow" and f.period == 1999).value > 0
    )
    assert next(m for m in metrics if m.id == "operating_cash_flow_growth_1999").value == -20


def test_zero_denominator_is_not_divided_or_replaced(source):
    blocks, _ = read_document(source, synthetic_filing(profit="0"))
    facts, _ = extract_facts(blocks, AS_OF)
    metrics, _, missing = calculate(facts)
    assert not any(m.id == "cash_profit_1999" for m in metrics)
    assert missing


def test_inconsistent_balance_is_not_repaired_to_fit(source):
    blocks, _ = read_document(
        source, synthetic_filing().replace(b"Total assets 500 450", b"Total assets 999 450")
    )
    facts, _ = extract_facts(blocks, AS_OF)
    _, findings, missing = calculate(facts)
    assert next(f for f in findings if f.id == "balance_mismatch_1999").status == "needs_review"
    assert next(f for f in facts if f.concept == "total_assets" and f.period == 1999).value == 999
    assert missing


def test_incompatible_units_are_not_combined(source):
    blocks, _ = read_document(source, synthetic_filing())
    facts, _ = extract_facts(blocks, AS_OF)
    next(f for f in facts if f.concept == "current_assets" and f.period == 1999).unit = "unknown"
    metrics, _, missing = calculate(facts)
    assert not any(m.id == "current_ratio_1999" for m in metrics)
    assert missing


def test_scale_applies_before_ratio(source):
    blocks, _ = read_document(source, synthetic_filing())
    facts, _ = extract_facts(blocks, AS_OF)
    fact = next(f for f in facts if f.concept == "current_assets" and f.period == 1999)
    fact.value, fact.scale = Decimal(200_000), 1000
    metrics, _, _ = calculate(facts)
    assert next(m for m in metrics if m.id == "current_ratio_1999").value == 2
