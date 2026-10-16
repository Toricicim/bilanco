"""Counterexamples found by the six-reviewer audit; no model/network/production DB."""

from decimal import Decimal

import pytest
import test_assessment_evaluation as ev
from conftest import FakeCodex, synthetic_filing
from test_assessment import CONTROL, ROLE, TRADE, check, draft, packet
from test_assessment import analysis as analysis
from test_assessment_evaluation import case, result

from bilanco.assessment import _merge_and_sort, run_assessment, validate_review
from bilanco.assessment_models import RelationReview
from bilanco.calculations import calculate, overall
from bilanco.cli import main
from bilanco.config import AS_OF
from bilanco.documents import archive_identity_ok, extract_facts, read_document
from bilanco.models import Block, Candidate, Extraction, Finding, Locator
from bilanco.pipeline import run_analysis


def test_actual_officer_controlled_consulting_company_is_not_routine_employment(analysis):
    trade = "Example Company paid Counterparty A $10 million under a consulting services agreement."
    analysis.blocks[0].text = "\n".join([ROLE, trade, CONTROL])
    d = draft(
        transaction=check("yes", trade),
        same_parties=check("yes", ROLE + "\n" + trade),
        financial_effect=check(),
    )
    accepted, rejected = validate_review(RelationReview(cases=[d]), packet(analysis))
    assert not rejected and accepted[0].priority == "first_review"
    d.kind = "employment"
    accepted, rejected = validate_review(RelationReview(cases=[d]), packet(analysis))
    assert not rejected and accepted[0].priority == "unassessed"  # contradictory model label


@pytest.mark.parametrize(
    "trade",
    [
        "Example Company has never conducted any transaction with Counterparty A.",
        "Example Company proposes to sell assets to Counterparty A next year; no transaction has occurred.",
        "Example Company did not complete a transaction with Counterparty A.",
    ],
)
def test_explicit_negative_or_proposed_transaction_cannot_be_positive(analysis, trade):
    analysis.blocks[0].text = "\n".join([ROLE, trade, CONTROL])
    d = draft(
        transaction=check("yes", trade),
        same_parties=check("yes", ROLE + "\n" + trade),
        financial_effect=check(),
    )
    accepted, rejected = validate_review(RelationReview(cases=[d]), packet(analysis))
    assert not accepted and rejected[0]["reason"] == "transaction_negated_or_proposed"


def test_explicit_negative_independent_control_is_rejected(analysis):
    text = "There was no independent valuation or audit committee review of this transaction."
    analysis.blocks[0].text += "\n" + text
    accepted, rejected = validate_review(
        RelationReview(
            cases=[draft(controls=check("yes", text), control_basis="reported_independent")]
        ),
        packet(analysis),
    )
    assert not accepted and rejected[0]["reason"] == "independent_control_negated"


def test_role_never_held_at_reporter_is_rejected(analysis):
    role = "Morgan manages Counterparty A; Morgan has never been an officer of Example Company."
    analysis.blocks[0].text = "\n".join([role, TRADE, CONTROL])
    analysis.findings[0].evidence[0].quote = role
    accepted, rejected = validate_review(
        RelationReview(
            cases=[
                draft(
                    executive_link=check("yes", role),
                    same_parties=check("yes", role + "\n" + TRADE),
                )
            ]
        ),
        packet(analysis),
    )
    assert not accepted and rejected[0]["reason"] == "negated_executive_role"


def test_distinct_transactions_in_same_block_keep_their_unknowns(analysis):
    loan = "Example Company loaned Counterparty A $50 million on December 15."
    analysis.blocks[0].text += "\n" + loan
    analysis.findings.append(
        Finding(
            id="loan",
            category="executive_conflict",
            status="needs_review",
            title="loan",
            explanation="synthetic",
            evidence=[Locator(block_id="b", quote=loan)],
        )
    )
    d = draft(
        finding_ids=["loan"],
        transaction=check("yes", loan),
        same_parties=check("yes", loan),
        financial_effect=check(),
        controls=check(),
        control_basis="not_found",
        counter_evidence=[],
    )
    accepted, rejected = validate_review(RelationReview(cases=[draft(), d]), packet(analysis))
    assert not rejected and len(accepted) == 2
    merged = _merge_and_sort(accepted, analysis)
    assert len(merged) == 2
    assert {c.relation.controls.answer for c in merged} == {"yes", "unknown"}
    assert next(c for c in merged if "loan" in c.source_finding_ids).unknowns


@pytest.mark.parametrize("scope", ["multiple", "unknown"])
def test_pooled_or_unscoped_model_transaction_is_not_accepted(analysis, scope):
    accepted, rejected = validate_review(
        RelationReview(cases=[draft(transaction_scope=scope)]), packet(analysis)
    )
    assert not accepted and rejected[0]["reason"] == "transaction_scope_not_single"


def test_multiple_distinct_transaction_spans_require_separate_cases(analysis):
    d = draft()
    d.transaction.evidence.append(Locator(block_id="b", quote=CONTROL))
    accepted, rejected = validate_review(RelationReview(cases=[d]), packet(analysis))
    assert not accepted and rejected[0]["reason"] == "transaction_evidence_not_atomic"


def test_explicit_internal_transfer_is_context_unless_executive_link_is_supported(analysis):
    text = "Counterparty A is a wholly owned subsidiary of Example Company. Example Company transferred assets to Counterparty A within its consolidated group."
    analysis.blocks[0].text = text
    analysis.findings[0].evidence[0].quote = text
    d = draft(
        kind="intragroup_transfer",
        executive="",
        classification_evidence=[Locator(block_id="b", quote=text)],
        executive_link=check(),
        transaction=check("yes", text),
        same_parties=check(),
        financial_effect=check(),
        controls=check(),
        control_basis="not_found",
        counter_evidence=[],
    )
    accepted, rejected = validate_review(RelationReview(cases=[d]), packet(analysis))
    assert not rejected and accepted[0].rule_id == "intragroup_transfer"
    analysis.blocks[0].text += "\n" + ROLE
    d.executive = "Morgan"
    d.executive_link = check("yes", ROLE)
    d.same_parties = check("yes", text + "\n" + ROLE)
    accepted, rejected = validate_review(RelationReview(cases=[d]), packet(analysis))
    assert not rejected and accepted[0].priority == "first_review"


@pytest.mark.parametrize(
    "label,amount,accepted",
    [
        ("used in", "60", False),
        ("used in", "(60)", True),
        ("provided by", "60", True),
        ("used in", "-60", True),
        ("provided by", "(60)", True),
    ],
)
def test_cash_flow_label_does_not_invent_positive_cash(source, label, amount, accepted):
    content = synthetic_filing(operating=amount).replace(b"provided by", label.encode())
    blocks, _ = read_document(source, content)
    facts, rejected = extract_facts(blocks, AS_OF)
    values = [f for f in facts if f.concept == "operating_cash_flow" and f.period == 1999]
    assert bool(values) == accepted
    if label == "used in" and accepted:
        assert values[0].value < 0
    if not accepted:
        assert any(r["reason"] == "cash_flow_sign_ambiguous" for r in rejected)
        _, findings, _ = calculate(facts)
        assert not any(f.id == "cash_profit_1999" and "pozitif." in f.explanation for f in findings)


def test_negative_equity_is_a_known_condition_not_missing_data(source):
    blocks, _ = read_document(source, synthetic_filing())
    facts, _ = extract_facts(blocks, AS_OF)
    for f in facts:
        if f.concept == "equity":
            f.value = Decimal(-50)
        if f.concept == "total_assets":
            f.value = Decimal(500)
        if f.concept == "total_liabilities":
            f.value = Decimal(550)
    metrics, findings, missing = calculate(facts)
    assert any(f.id == "negative_equity_1999" and f.status == "signal" for f in findings)
    assert not any(m.id == "long_debt_equity_1999" for m in metrics)
    assert not missing and overall(findings, missing) == "inceleme_isareti_var"


def test_restatement_in_different_word_order_is_not_original_identity():
    blocks = [
        Block(
            id="b",
            source_id="s",
            line_start=1,
            text="Enron 1999 Annual Report\nCONSOLIDATED BALANCE SHEETS\nRestated financial statements issued 2001-11-08",
        )
    ]
    assert not archive_identity_ok(blocks)


def test_legacy_archive_analysis_cannot_be_reassessed_as_historically_verified(
    analysis, settings, memory_store
):
    analysis.sources[0].provenance = "archive_copy"

    class NoAI:
        calls = 0
        receipts = []

        def assess_relations(self, _):
            pytest.fail("unverified archive reached model")

    assessed = run_assessment(settings, memory_store, analysis, codex=NoAI())
    assert assessed.status == "failed" and assessed.ai["calls"] == 0
    assert not any(c.priority in {"first_review", "further_review"} for c in assessed.cases)


def test_ctrl_c_saves_partial_analysis_and_does_not_start_next_stage(
    settings, memory_store, acquirer, monkeypatch, capsys
):
    class Interrupted(FakeCodex):
        def extract(self, _):
            raise KeyboardInterrupt

    monkeypatch.setattr("bilanco.cli.Settings.load", lambda: settings)
    monkeypatch.setattr("bilanco.cli.Store", lambda _: memory_store)
    monkeypatch.setattr(
        "bilanco.cli.run_analysis",
        lambda settings, store, **_: run_analysis(
            settings, store, acquirer=acquirer, codex=Interrupted()
        ),
    )
    monkeypatch.setattr(
        "bilanco.cli.run_assessment",
        lambda *a, **k: pytest.fail("assessment started after cancellation"),
    )
    assert main(["analyze", "--company", "enron", "--as-of", "2000-03-31"]) == 130
    assert '"cancelled": true' in capsys.readouterr().out
    saved = next(iter(memory_store.runs.values()))
    assert saved["ai"]["cancelled"] and saved["facts"]
    assert (settings.data_dir / "runs" / saved["run_id"] / "analysis.json").exists()


def test_all_negatives_as_further_review_or_abstention_fail_full_priority_gate():
    for priority in ("further_review", "unassessed"):
        report = ev.measure(result(priority), [case()])
        assert not report["regression_gate_passed"]
        assert report["priority_mismatches"] == ["one"]
    assert ev.measure(result("context"), [case()])["regression_gate_passed"]


def test_end_to_end_measures_extractor_misses_and_keeps_labels_out_of_inputs():
    row = case(True) | {"id": "one", "text": ROLE + "\n" + TRADE}
    raw = ev.evaluation.make_analysis([row], seed_candidates=False)
    assert not raw.findings

    class Empty(FakeCodex):
        pass

    mapping, extraction = ev.evaluation.extract_from_blocks(raw, Empty())
    assert not mapping and extraction["candidate_count"] == 0
    assessed = result("context")
    assessed.cases = []
    report = ev.measure(assessed, [row], candidate_blocks=mapping)
    assert report["false_negative"] == 1 and report["missed_positive_extractions"] == ["one"]
    assert not report["regression_gate_passed"]

    class Extracted(FakeCodex):
        def extract(self, blocks):
            self.calls += 1
            return Extraction(
                candidates=[
                    Candidate(
                        kind="executive_conflict",
                        block_id=blocks[0].id,
                        quote=ROLE,
                        actor="Morgan",
                        counterparty="Counterparty A",
                    )
                ]
            )

    mapping, _ = ev.evaluation.extract_from_blocks(raw, Extracted())
    assert len(raw.findings) == 1 and mapping[raw.findings[0].id] == [ev.case_key("one")]


@pytest.mark.parametrize(
    "role,trade",
    [
        (
            "Morgan is not only an officer of Example Company but also manages Counterparty A.",
            TRADE,
        ),
        (ROLE, "With no independent review, Example Company transacted with Counterparty A."),
    ],
)
def test_positive_correlative_role_and_missing_control_do_not_negate_transaction(
    analysis, role, trade
):
    analysis.blocks[0].text = "\n".join([role, trade, CONTROL])
    analysis.findings[0].evidence[0].quote = role
    d = draft(
        executive_link=check("yes", role),
        transaction=check("yes", trade),
        same_parties=check("yes", role + "\n" + trade),
        financial_effect=check(),
    )
    accepted, rejected = validate_review(RelationReview(cases=[d]), packet(analysis))
    assert not rejected and accepted[0].priority == "first_review"


def test_did_not_sell_cannot_be_a_completed_transaction(analysis):
    trade = "Example Company did not sell assets to Counterparty A."
    analysis.blocks[0].text = "\n".join([ROLE, trade, CONTROL])
    d = draft(
        transaction=check("yes", trade),
        same_parties=check("yes", ROLE + "\n" + trade),
        financial_effect=check(),
    )
    accepted, rejected = validate_review(RelationReview(cases=[d]), packet(analysis))
    assert not accepted and rejected[0]["reason"] == "transaction_negated_or_proposed"


def test_two_actions_in_one_quote_cannot_pool_controls_even_if_model_claims_single(analysis):
    trade = "Example Company sold an asset to Counterparty A in June and loaned Counterparty A $50 million in December."
    analysis.blocks[0].text = "\n".join([ROLE, trade, CONTROL])
    d = draft(
        transaction=check("yes", trade),
        same_parties=check("yes", ROLE + "\n" + trade),
        financial_effect=check(),
    )
    accepted, rejected = validate_review(RelationReview(cases=[d]), packet(analysis))
    assert not accepted and rejected[0]["reason"] == "multiple_transaction_actions"


def test_model_cannot_pool_two_finding_ids_into_one_answer_tuple(analysis):
    analysis.findings.append(analysis.findings[0].model_copy(update={"id": "second"}))
    d = draft(finding_ids=["candidate_a", "second"])
    accepted, rejected = validate_review(RelationReview(cases=[d]), packet(analysis))
    assert not accepted and rejected[0]["reason"] == "pooled_finding_ids"


def test_two_transaction_passage_has_stage_specific_reference_not_false_alarm():
    row = case() | {
        "expected_priority_provisional": "unassessed",
        "expected_end_to_end_priority_provisional": "first_review",
    }
    assert ev.measure(result("unassessed"), [row])["regression_gate_passed"]
    mapped = {"extracted-sale": [ev.case_key("one")]}
    assessed = result("first_review")
    assessed.cases[0].source_finding_ids = ["extracted-sale"]
    report = ev.measure(assessed, [row], candidate_blocks=mapped, stage="end-to-end")
    assert report["regression_gate_passed"] and report["false_positive"] == 0
    assert report["true_positive"] == 1


def test_assessment_human_labels_are_not_end_to_end_human_gold():
    row = case(True)
    row["reviewer_a"] = {"reviewer_id": "a", "first_review": False}
    row["reviewer_b"] = {"reviewer_id": "b", "first_review": False}
    report = ev.measure(result("first_review"), [row], stage="end-to-end")
    assert report["human_agreed_cases"] == 0 and report["human_review_pending"] == 1
    assert report["label_basis"] != "two_reviewers"
    assert report["priority_label_basis"] != "two_reviewers"


def test_end_to_end_human_priority_overrides_provisional_independently():
    row = case(True)
    row["reviewer_a"] = {"reviewer_id": "a", "first_review": True, "end_to_end_priority": "context"}
    row["reviewer_b"] = {
        "reviewer_id": "b",
        "first_review": False,
        "end_to_end_priority": "context",
    }
    report = ev.measure(result("context"), [row], stage="end-to-end")
    assert report["human_agreed_cases"] == 1 and report["label_basis"] == "two_reviewers"
    assert report["true_negative"] == 1 and report["true_positive"] == 0
    assert report["regression_gate_passed"]
