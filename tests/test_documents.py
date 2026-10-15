import io
from decimal import Decimal

from conftest import synthetic_filing
from reportlab.pdfgen.canvas import Canvas

from bilanco.calculations import calculate
from bilanco.config import AS_OF
from bilanco.documents import extract_facts, read_document
from bilanco.models import Block


def facts_for(source, **kwargs):
    blocks, issues = read_document(source, synthetic_filing(**kwargs))
    assert not issues
    return extract_facts(blocks, AS_OF)


def test_extracts_financial_rows_without_ai(source):
    facts, rejected = facts_for(source)
    assert not rejected
    lookup = {(f.concept, f.period): f for f in facts}
    assert lookup[("current_assets", 1999)].value == Decimal(200)
    assert lookup[("current_assets", 1999)].scale == 1_000_000
    assert lookup[("operating_cash_flow", 1998)].value == Decimal(50)
    assert len([f for f in facts if f.concept == "net_income"]) == 2


def test_year_order_is_read_from_source_not_assumed(source):
    facts, _ = facts_for(source, years="1998 1999")
    assert next(f for f in facts if f.concept == "current_assets" and f.period == 1999).value == 150


def test_ambiguous_columns_are_not_guessed(source):
    facts, rejected = facts_for(source, current="200 300")
    assert not any(f.concept == "current_assets" for f in facts)
    assert any(r["reason"] == "ambiguous_table_columns" for r in rejected)


def test_source_number_change_changes_computed_ratio(source):
    before, _ = facts_for(source)
    after, _ = facts_for(source, current="80")
    a, _, _ = calculate(before)
    b, _, _ = calculate(after)
    assert next(m for m in a if m.id == "current_ratio_1999").value == 2
    assert next(m for m in b if m.id == "current_ratio_1999").value == Decimal("0.8")


def test_negative_values_and_scale_are_preserved(source):
    facts, _ = facts_for(source, operating="(12)")
    fact = next(f for f in facts if f.concept == "operating_cash_flow" and f.period == 1999)
    assert fact.value == -12 and fact.scale == 1_000_000


def test_conflicting_source_rows_are_removed(source):
    content = synthetic_filing().replace(
        b"Total current assets 200 150",
        b"Total current assets 200 150\nTotal current assets 999 150",
    )
    blocks, _ = read_document(source, content)
    facts, rejected = extract_facts(blocks, AS_OF)
    assert not any(f.concept == "current_assets" and f.period == 1999 for f in facts)
    assert any(r["reason"] == "conflicting_values" for r in rejected)


def test_notes_are_not_misread_as_balance_table(source):
    content = synthetic_filing() + b"\nTotal current assets 999 888"
    blocks, _ = read_document(source, content)
    facts, _ = extract_facts(blocks, AS_OF)
    assert next(f for f in facts if f.concept == "current_assets" and f.period == 1999).value == 200


def test_pdf_reader_keeps_page_and_block_location(source):
    stream = io.BytesIO()
    canvas = Canvas(stream)
    canvas.drawString(30, 750, "Synthetic document page one")
    canvas.showPage()
    canvas.drawString(30, 750, "Synthetic document page two")
    canvas.save()
    blocks, issues = read_document(source, stream.getvalue())
    assert not issues
    assert [b.page for b in blocks] == [1, 2]
    assert blocks[0].id != blocks[1].id


def test_blank_scan_is_reported_not_hallucinated(source):
    stream = io.BytesIO()
    canvas = Canvas(stream)
    canvas.showPage()
    canvas.save()
    blocks, issues = read_document(source, stream.getvalue())
    assert blocks == []
    assert any("OCR" in issue for issue in issues)


def test_no_unit_header_means_no_accepted_amounts(source):
    content = synthetic_filing().replace(b"(In millions of dollars)", b"")
    blocks, _ = read_document(source, content)
    facts, _ = extract_facts(blocks, AS_OF)
    assert not facts


def test_malformed_pdf_fails_closed(source):
    blocks, issues = read_document(source, b"%PDF-not-a-pdf")
    assert not blocks and issues


def test_natural_date_header_is_bound_to_columns(source):
    facts, _ = facts_for(source, years="December 31, 1999 1998")
    assert next(f for f in facts if f.concept == "current_assets" and f.period == 1999).value == 200


def test_bad_comma_grouping_and_dashes_are_not_numbers(source):
    facts, rejected = facts_for(source, current="1,23", current_old="--")
    assert not any(f.concept == "current_assets" for f in facts)
    assert any(r["reason"] == "amount_missing_or_invalid" for r in rejected)


def test_random_prose_years_not_a_table():
    block = Block(
        id="x",
        source_id="s",
        line_start=1,
        text="We compared 1999 and 1998.\nTotal current assets 200 100",
    )
    assert extract_facts([block], AS_OF)[0] == []


def test_legacy_edgar_aligned_tables_keep_numbers_and_evidence(source):
    # Invented amounts, with the TABLE/CAPTION/S/C format used in old EDGAR files.
    content = b"""<TABLE>
CONSOLIDATED BALANCE SHEET
<CAPTION>
(In millions, except shares)          1999    1998
<S>                                   <C>     <C>
Cash and cash equivalents             $30     $20
Total current assets                  200     150
</TABLE>
<TABLE>
CONSOLIDATED INCOME STATEMENT
<CAPTION>
(In millions, except per share amounts) 1999 1998
<S>                                     <C>  <C>
Net income                              $40   $30
Net income before accounting changes     41    31
</TABLE>
<TABLE>
CONSOLIDATED STATEMENT OF CASH FLOWS
<CAPTION>
(In millions)                          1999   1998
<S>                                    <C>    <C>
Net Cash Provided by Operating
 Activities                             $60    $50
</TABLE>"""
    blocks, issues = read_document(source, content)
    facts, rejected = extract_facts(blocks, AS_OF)
    assert not issues and not rejected
    lookup = {(f.concept, f.period): f for f in facts}
    assert lookup[("current_assets", 1999)].value == 200
    assert lookup[("net_income", 1999)].value == 40
    cash = lookup[("operating_cash_flow", 1999)]
    assert cash.value == 60 and cash.scale == 1_000_000
    assert "Operating\n Activities" in cash.evidence.quote
    block = next(b for b in blocks if b.id == cash.evidence.block_id)
    assert cash.evidence.quote in block.text


def test_unrecognized_statement_cannot_reuse_previous_table_context(source):
    content = synthetic_filing().replace(
        b"NOTES TO CONSOLIDATED FINANCIAL STATEMENTS",
        b"CONSOLIDATED STATEMENT OF COMPREHENSIVE INCOME\n"
        b"(In millions of dollars)\n1999 1998\nNet income 900 800\n"
        b"NOTES TO CONSOLIDATED FINANCIAL STATEMENTS",
    )
    blocks, _ = read_document(source, content)
    facts, rejected = extract_facts(blocks, AS_OF)
    assert not rejected
    assert next(f for f in facts if f.concept == "net_income" and f.period == 1999).value == 40


def test_units_do_not_turn_arbitrary_prose_into_year_headers(source):
    content = synthetic_filing().replace(b"1999 1998", b"(In millions) We compared 1999 and 1998.")
    blocks, _ = read_document(source, content)
    assert extract_facts(blocks, AS_OF)[0] == []


def test_heading_mentioned_in_notes_does_not_reopen_statement(source):
    content = synthetic_filing() + (
        b"\nConsolidated Income Statement in the same manner as the hedged item.\n"
        b"(In millions) 1999 1998\nNet income 900 800\n"
    )
    blocks, _ = read_document(source, content)
    facts, rejected = extract_facts(blocks, AS_OF)
    assert not rejected
    assert next(f for f in facts if f.concept == "net_income" and f.period == 1999).value == 40
