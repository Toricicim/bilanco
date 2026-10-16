"""Explicit live-model regression on invented passages; never financial acquisition.

uv run python evaluation/evaluate.py --split test --run-model
uv run python evaluation/evaluate.py --split test --predictions path/to/assessment.json
"""

import argparse
import json
import uuid
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from bilanco.assessment import run_assessment
from bilanco.assessment_models import Assessment
from bilanco.config import AS_OF, Settings
from bilanco.models import Analysis, Block, Finding, Locator, Source
from bilanco.storage import write_json

CORPUS = Path(__file__).with_name("related_party_cases.json")


def case_key(identifier: str) -> str:
    # Descriptive fixture names can reveal the expected answer to a judge.
    return sha256(identifier.encode()).hexdigest()[:24]


def make_analysis(cases: list[dict]) -> Analysis:
    analysis = Analysis(
        run_id=str(uuid.uuid4()),
        company="Fictional Reporter plc",
        as_of=AS_OF,
        created_at=datetime.now(UTC),
        status="complete",
    )
    for row in cases:
        key = case_key(row["id"])
        analysis.sources.append(
            Source(
                id=key,
                url="https://synthetic.invalid/" + key,
                sha256="0" * 64,
                media_type="text/plain",
                retrieved_at=datetime.now(UTC),
                path="synthetic",
                publication_date=AS_OF,
                publication_proof="Invented fixture, not a public filing",
                provenance="dated_official",
                version_note="Synthetic test only",
            )
        )
        analysis.blocks.append(Block(id=key, source_id=key, line_start=1, text=row["text"]))
        analysis.findings.append(
            Finding(
                id=key,
                category="executive_conflict",
                status="needs_review",
                title="Synthetic unverified candidate",
                explanation="No historical company data",
                evidence=[Locator(block_id=key, quote=row["text"])],
            )
        )
    return analysis


def measure(result: Assessment, cases: list[dict]) -> dict:
    predictions = {
        fid: (None if c.priority == "unassessed" else c.priority == "first_review")
        for c in result.cases
        for fid in c.source_finding_ids
    }
    expected_ids = {case_key(r["id"]) for r in cases}
    if set(predictions) != expected_ids:
        raise ValueError("Predictions must cover exactly the selected corpus cases")
    rows, agreements = [], 0
    for row in cases:
        a, b = row["reviewer_a"], row["reviewer_b"]
        agreed = bool(
            isinstance(a, dict)
            and isinstance(b, dict)
            and a.get("reviewer_id")
            and b.get("reviewer_id")
            and a["reviewer_id"] != b["reviewer_id"]
            and type(a.get("first_review")) is bool
            and type(b.get("first_review")) is bool
            and a["first_review"] == b["first_review"]
        )
        agreements += agreed
        expected = a["first_review"] if agreed else row["expected_first_review_provisional"]
        rows.append(
            {
                "id": row["id"],
                "expected": expected,
                "predicted": predictions[case_key(row["id"])],
                "human_agreement": agreed,
                "critical_negative": row["critical_negative"],
            }
        )
    tp = sum(r["expected"] and r["predicted"] is True for r in rows)
    fp = sum(not r["expected"] and r["predicted"] is True for r in rows)
    fn = sum(r["expected"] and r["predicted"] is not True for r in rows)
    tn = sum(not r["expected"] and r["predicted"] is False for r in rows)
    abstentions = [r["id"] for r in rows if r["predicted"] is None]
    false_alarms = [
        r["id"]
        for r in rows
        if not r["expected"] and r["critical_negative"] and r["predicted"] is True
    ]
    return {
        "synthetic": True,
        "assessment_id": result.id,
        "assessment_status": result.status,
        "rule_version": result.rule_version,
        "metric_version": "priority-abstention-1",
        "case_id_policy": "opaque-case-1",
        "label_basis": "two_reviewers"
        if agreements == len(rows)
        else "provisional_or_mixed_not_human_gold",
        "human_agreed_cases": agreements,
        "human_review_pending": len(rows) - agreements,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "abstentions": abstentions,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "critical_false_alarms": false_alarms,
        "regression_gate_passed": result.status == "complete"
        and not false_alarms
        and fn == 0
        and fp == 0,
        "fraud_prediction_validated": False,
        "cases": rows,
    }


class EvaluationStore:
    """In-memory sink for a synthetic evaluation; no production database writes."""

    def start_assessment(self, _):
        pass

    def finish_assessment(self, _):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-model", action="store_true")
    group.add_argument("--predictions", type=Path)
    args = parser.parse_args()
    cases = [r for r in json.loads(CORPUS.read_text())["cases"] if r["split"] == args.split]
    settings = Settings.load()
    output = settings.data_dir / "evaluations" / str(uuid.uuid4())
    output.mkdir(parents=True, exist_ok=False)
    if args.run_model:
        from dataclasses import replace

        result = run_assessment(
            replace(settings, data_dir=output),
            EvaluationStore(),
            make_analysis(cases),
            progress=print,
        )
    else:
        result = Assessment.model_validate_json(args.predictions.read_text())
    report = measure(result, cases)
    report["split"] = args.split
    write_json(output / "evaluation.json", report)
    print(
        json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False, indent=2)
    )
    print("Report:", output / "evaluation.json")
    return 0 if report["regression_gate_passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
