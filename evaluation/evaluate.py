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

from bilanco.ai import AIError, Codex, validate_candidates
from bilanco.assessment import run_assessment
from bilanco.assessment_models import Assessment
from bilanco.config import AS_OF, Settings
from bilanco.models import Analysis, Block, Finding, Locator, Source
from bilanco.pipeline import chunks
from bilanco.storage import write_json

CORPUS = Path(__file__).with_name("related_party_cases.json")


def case_key(identifier: str) -> str:
    # Descriptive fixture names can reveal the expected answer to a judge.
    return sha256(identifier.encode()).hexdigest()[:24]


def make_analysis(cases: list[dict], *, seed_candidates: bool = True) -> Analysis:
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
        if not seed_candidates:
            continue
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


def measure(
    result: Assessment,
    cases: list[dict],
    *,
    candidate_blocks: dict | None = None,
    stage: str = "assessment",
) -> dict:
    priorities = ["first_review", "further_review", "context", "unassessed"]
    expected_ids = {case_key(r["id"]) for r in cases}
    actual = {}
    for c in result.cases:
        for fid in c.source_finding_ids:
            targets = candidate_blocks.get(fid, []) if candidate_blocks is not None else [fid]
            for key in targets:
                if key not in expected_ids:
                    raise ValueError("Prediction contains an unknown corpus case")
                previous = actual.get(key)
                if previous is None or priorities.index(c.priority) < priorities.index(previous):
                    actual[key] = c.priority
    if candidate_blocks is None and set(actual) != expected_ids:
        raise ValueError("Predictions must cover exactly the selected corpus cases")
    # In end-to-end mode no candidate means no alert, not an examined relation.
    # Candidate coverage and positive misses remain separate visible measurements.
    detected_ids = set(actual)
    for key in expected_ids:
        actual.setdefault(key, "context")
    predictions = {
        key: None if value == "unassessed" else value == "first_review"
        for key, value in actual.items()
    }
    rows, agreements = [], 0
    for row in cases:
        a, b = row["reviewer_a"], row["reviewer_b"]
        priority_field = "priority" if stage == "assessment" else "end_to_end_priority"
        proposed = (
            row.get(
                "expected_end_to_end_priority_provisional", row.get("expected_priority_provisional")
            )
            if stage == "end-to-end"
            else row.get("expected_priority_provisional")
        )
        distinct_reviewers = bool(
            isinstance(a, dict)
            and isinstance(b, dict)
            and a.get("reviewer_id")
            and b.get("reviewer_id")
            and a["reviewer_id"] != b["reviewer_id"]
        )
        if stage == "end-to-end":
            # A label for a seeded candidate is NOT an end-to-end reference.
            priority_agreed = bool(
                distinct_reviewers
                and a.get(priority_field) in priorities
                and a.get(priority_field) == b.get(priority_field)
            )
            agreed = priority_agreed
            expected_priority = a[priority_field] if agreed else proposed
            expected = (
                expected_priority == "first_review"
                if expected_priority is not None
                else row["expected_first_review_provisional"]
            )
        else:
            agreed = bool(
                distinct_reviewers
                and type(a.get("first_review")) is bool
                and type(b.get("first_review")) is bool
                and a["first_review"] == b["first_review"]
            )
            expected = a["first_review"] if agreed else row["expected_first_review_provisional"]
            priority_agreed = bool(
                agreed
                and a.get(priority_field) in priorities
                and a.get(priority_field) == b.get(priority_field)
                and (a[priority_field] == "first_review") == expected
            )
            expected_priority = (
                a[priority_field] if priority_agreed else None if agreed else proposed
            )
        agreements += agreed
        if expected_priority is not None and (
            expected_priority not in priorities or (expected_priority == "first_review") != expected
        ):
            raise ValueError("Inconsistent provisional priority/first_review labels")

        rows.append(
            {
                "id": row["id"],
                "expected": expected,
                "predicted": predictions[case_key(row["id"])],
                "human_agreement": agreed,
                "critical_negative": row["critical_negative"],
                "expected_priority": expected_priority,
                "predicted_priority": actual[case_key(row["id"])],
                "candidate_found": case_key(row["id"]) in detected_ids,
                "human_priority_agreement": priority_agreed,
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
    matrix = {truth: {pred: 0 for pred in priorities} for truth in priorities}
    mismatches = []
    for row in rows:
        if row["expected_priority"] is not None:
            matrix[row["expected_priority"]][row["predicted_priority"]] += 1
            if row["expected_priority"] != row["predicted_priority"]:
                mismatches.append(row["id"])
    full_labels = all(r["expected_priority"] in priorities for r in rows)
    unwanted_alerts = [
        r["id"]
        for r in rows
        if r["expected_priority"] in {"context", "unassessed"}
        and r["predicted_priority"] in {"first_review", "further_review"}
    ]
    avoidable_abstentions = [
        r["id"]
        for r in rows
        if r["expected_priority"] in {"context", "first_review", "further_review"}
        and r["predicted_priority"] == "unassessed"
    ]
    per_class = {}
    for label in priorities:
        predicted = sum(matrix[t][label] for t in priorities)
        support = sum(matrix[label].values())
        per_class[label] = {
            "support": support,
            "precision": matrix[label][label] / predicted if predicted else None,
            "recall": matrix[label][label] / support if support else None,
        }
    top_ids = []
    for c in result.cases:
        if c.priority not in {"first_review", "further_review"}:
            continue
        for fid in c.source_finding_ids:
            for key in candidate_blocks.get(fid, []) if candidate_blocks is not None else [fid]:
                if key not in top_ids:
                    top_ids.append(key)
    top_ids = top_ids[:3]
    relevant = {
        case_key(r["id"])
        for r in rows
        if r["expected_priority"] in {"first_review", "further_review"}
    }
    return {
        "synthetic": True,
        "measurement_unit": "passage",
        "assessment_id": result.id,
        "assessment_status": result.status,
        "rule_version": result.rule_version,
        "metric_version": "priority-four-class-2",
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
        "confusion_matrix": matrix,
        "per_class": per_class,
        "top_three_topic_precision": sum(key in relevant for key in top_ids) / len(top_ids)
        if top_ids and full_labels
        else None,
        "top_three_case_ids": top_ids,
        "priority_labels_complete": full_labels,
        "priority_label_basis": "two_reviewers"
        if all(r["human_priority_agreement"] for r in rows)
        else "provisional_or_missing_not_human_gold",
        "priority_mismatches": mismatches,
        "unnecessary_alerts": unwanted_alerts,
        "avoidable_abstentions": avoidable_abstentions,
        "candidate_coverage": len(detected_ids) / len(rows) if rows else None,
        "missed_positive_extractions": [
            r["id"] for r in rows if r["expected"] and not r["candidate_found"]
        ],
        "regression_gate_passed": full_labels
        and not mismatches
        and result.status == "complete"
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


def extract_from_blocks(analysis: Analysis, ai) -> tuple[dict, dict]:
    """Actual stage-1 extractor, including source validation; no seeded candidates."""
    analysis.findings = []
    rejected, errors = [], []
    for package in chunks(analysis.blocks, 24000):
        try:
            accepted, invalid = validate_candidates(ai.extract(package).candidates, package)
            analysis.findings.extend(accepted)
            rejected.extend(invalid)
        except AIError as exc:
            errors.append(str(exc))
            break
    mapping = {f.id: sorted({r.block_id for r in f.evidence}) for f in analysis.findings}
    return mapping, {
        "stage": "end-to-end",
        "calls": ai.calls,
        "candidate_count": len(analysis.findings),
        "rejected": rejected,
        "errors": errors,
    }


def keyword_baseline(cases: list[dict]) -> Assessment:
    """Deliberately simple, frozen comparator; not a validated financial model."""
    import re

    from bilanco.assessment_models import ReviewCase

    result = Assessment(
        id=str(uuid.uuid4()),
        source_run_id="synthetic-keyword",
        source_analysis_sha256="0" * 64,
        company="Fictional Reporter plc",
        as_of=AS_OF,
        created_at=datetime.now(UTC),
        source_analysis_status="complete",
        status="complete",
    )
    for row in cases:
        text = row["text"].lower()
        hit = bool(
            re.search(r"officer|treasurer", text)
            and re.search(r"manag|control", text)
            and re.search(r"sold|purchased|made a loan|transferred|paid", text)
            and not re.search(r"\bno\b|\bnot\b|\bnever\b|propos", text)
        )
        result.cases.append(
            ReviewCase(
                id=case_key(row["id"]),
                priority="first_review" if hit else "context",
                rule_id="keyword-baseline-1",
                title="Synthetic keyword comparator",
                explanation="Unvalidated comparator",
                source_finding_ids=[case_key(row["id"])],
                model_assessed=False,
            )
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--stage", choices=["assessment", "end-to-end"], default="assessment")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-model", action="store_true")
    group.add_argument("--predictions", type=Path)
    group.add_argument("--baseline", action="store_true")
    parser.add_argument(
        "--candidate-map", type=Path, help="Recorded end-to-end candidate mapping for replay"
    )
    args = parser.parse_args()
    if args.predictions and args.stage == "end-to-end" and not args.candidate_map:
        parser.error("End-to-end replay needs --candidate-map; never assume candidates were found")
    cases = [r for r in json.loads(CORPUS.read_text())["cases"] if r["split"] == args.split]
    settings = Settings.load()
    output = settings.data_dir / "evaluations" / str(uuid.uuid4())
    output.mkdir(parents=True, exist_ok=False)
    mapping, extraction = None, {"stage": args.stage}
    if args.baseline:
        result = keyword_baseline(cases)
    elif args.run_model:
        from dataclasses import replace

        analysis = make_analysis(cases, seed_candidates=args.stage != "end-to-end")
        remaining = settings.max_ai_calls
        if args.stage == "end-to-end":
            ai = Codex(settings, output / "extraction-ai")
            mapping, extraction = extract_from_blocks(analysis, ai)
            remaining -= ai.calls
            write_json(output / "candidate-map.json", mapping)
        result = run_assessment(
            replace(settings, data_dir=output),
            EvaluationStore(),
            analysis,
            remaining_calls=remaining,
            progress=print,
        )
        if extraction.get("errors") or extraction.get("rejected"):
            result.status = "partial"
    else:
        result = Assessment.model_validate_json(args.predictions.read_text())
        if args.candidate_map:
            mapping = json.loads(args.candidate_map.read_text())
    report = measure(result, cases, candidate_blocks=mapping, stage=args.stage)
    report.update(
        {
            "split": args.split,
            "stage": args.stage,
            "method": "keyword-baseline-1" if args.baseline else "llm",
            "extraction": extraction,
            "assessment_calls": result.ai.get("calls", 0),
            "total_calls": extraction.get("calls", 0) + result.ai.get("calls", 0),
            "human_validation_complete": False,
        }
    )
    write_json(output / "assessment.json", result.model_dump(mode="json"))
    write_json(output / "evaluation.json", report)
    print(
        json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False, indent=2)
    )
    print("Report:", output / "evaluation.json")
    return 0 if report["regression_gate_passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
