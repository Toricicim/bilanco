import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

from bilanco.assessment_models import Assessment, ReviewCase
from bilanco.config import AS_OF

spec = importlib.util.spec_from_file_location(
    "assessment_evaluation", Path(__file__).resolve().parents[1] / "evaluation/evaluate.py"
)
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)
CORPUS, measure, case_key = evaluation.CORPUS, evaluation.measure, evaluation.case_key


def result(priority="unassessed", status="complete"):
    return Assessment(
        id="evaluation",
        source_run_id="synthetic",
        source_analysis_sha256="0" * 64,
        company="Synthetic",
        as_of=AS_OF,
        created_at=datetime.now(UTC),
        source_analysis_status="complete",
        status=status,
        cases=[
            ReviewCase(
                id="case",
                priority=priority,
                rule_id="test",
                title="test",
                explanation="test",
                source_finding_ids=[case_key("one")],
            )
        ],
    )


def case(expected=False):
    return {
        "id": "one",
        "expected_first_review_provisional": expected,
        "expected_priority_provisional": "first_review" if expected else "context",
        "critical_negative": not expected,
        "reviewer_a": None,
        "reviewer_b": None,
    }


def test_corpus_has_48_cases_disjoint_families_and_explicit_review_states():
    rows = json.loads(CORPUS.read_text())["cases"]
    assert len(rows) == 48
    assert len({r["id"] for r in rows}) == 48
    dev = [r for r in rows if r["split"] == "dev"]
    test = [r for r in rows if r["split"] == "test"]
    assert len(dev) == len(test) == 24
    assert not {r["family"] for r in dev} & {r["family"] for r in test}
    for row in rows:
        for name in ("reviewer_a", "reviewer_b"):
            review = row[name]
            assert review is None or (
                isinstance(review, dict)
                and review.get("reviewer_id")
                and type(review.get("first_review")) is bool
            )


def test_labels_reviewers_and_descriptive_ids_never_reach_the_model():
    from bilanco.assessment import make_packages

    row = json.loads(CORPUS.read_text())["cases"][0]
    row["reviewer_a"] = {"reviewer_id": "private-human-label", "first_review": True}
    packages, omitted = make_packages(evaluation.make_analysis([row]), 24000)
    assert not omitted
    serialized = json.dumps(packages)
    for hidden in (
        row["id"],
        "expected_first_review_provisional",
        "reviewer_a",
        "private-human-label",
        "critical_negative",
    ):
        assert hidden not in serialized


def test_unknown_is_not_a_successful_negative():
    report = measure(result(), [case()])
    assert report["true_negative"] == 0
    assert report["abstentions"] == ["one"]
    assert not report["fraud_prediction_validated"]


def test_unknown_positive_is_a_missed_positive_and_blocks_gate():
    report = measure(result(), [case(True)])
    assert report["false_negative"] == 1 and not report["regression_gate_passed"]


def test_same_reviewer_twice_cannot_produce_human_gold():
    row = case()
    row["reviewer_a"] = {"reviewer_id": "same", "first_review": False}
    row["reviewer_b"] = row["reviewer_a"].copy()
    report = measure(result("context"), [row])
    assert report["human_review_pending"] == 1
    assert report["label_basis"] != "two_reviewers"


def test_partial_result_cannot_pass_even_with_no_false_alarms():
    assert not measure(result("context", "partial"), [case()])["regression_gate_passed"]
