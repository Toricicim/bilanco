"""Offline evaluation tests with fabricated outcomes and files, not historical performance."""

import json

import pytest
from test_equity_review_v2 import healthy_snapshot

from bilanco.cli import main
from bilanco.equity_models import EquityAssessment, InvestorReview
from bilanco.equity_pipeline import canonical_hash
from bilanco.equity_study import evaluate_study


def case(root, settings, company, *, event=False, alert=False, unknown=False, split="test"):
    a = healthy_snapshot(settings)
    a.company_id = company
    a.run_id = company
    a.status = "partial"
    b = EquityAssessment(
        source_run_id=a.run_id,
        source_analysis_sha256=canonical_hash(a),
        company=a.company,
        as_of=a.as_of,
        outcome="yetersiz_veri"
        if unknown
        else "dikkat_gerektiriyor"
        if alert
        else "belirgin_isaret_yok",
        status=a.status,
        findings=[],
        coverage={},
        limitations=[],
        investor_review=InvestorReview(
            status="veri_yetersiz"
            if unknown
            else "inceleme_gerekli"
            if alert
            else "belirgin_ek_isaret_yok",
            message="Synthetic fixture only",
            finding_ids=[],
            incomplete_checks=[],
            limitations=[],
        ),
    )
    (root / f"{company}-analysis.json").write_text(a.model_dump_json())
    (root / f"{company}-assessment.json").write_text(b.model_dump_json())
    return {
        "company_id": company,
        "split": split,
        "analysis": f"{company}-analysis.json",
        "assessment": f"{company}-assessment.json",
        "target_event_observed": event,
        "event_date": "2025-06-01" if event else None,
        "followup_end": "2026-04-01",
        "label_source": "SYNTHETIC OUTCOME — NOT A REAL COMPANY EVENT",
    }


def manifest(root, cases, *, development=None):
    path = root / "study.json"
    path.write_text(
        json.dumps(
            {
                "target_definition": "SYNTHETIC ONLY: a fictional disclosure event in the next year",
                "horizon_days": 365,
                "rule_version": "tr-equity-review-4",
                "development_company_ids": development or [],
                "cases": cases,
            }
        )
    )
    return path


def test_true_alarms_false_alarms_and_unknowns_are_separate(settings, tmp_path):
    cases = [
        case(tmp_path, settings, "hit", event=True, alert=True),
        case(tmp_path, settings, "miss", event=True),
        case(tmp_path, settings, "false", alert=True),
        case(tmp_path, settings, "quiet"),
        case(tmp_path, settings, "unknown", unknown=True),
    ]
    result = evaluate_study(manifest(tmp_path, cases))
    counts = result["results"]["test"]["investor_review"]
    assert counts["companies"] == 5 and counts["assessed"] == 4 and counts["abstained"] == 1
    assert counts["effective_event_recall"] == 0.5
    assert counts["false_positive_rate_among_assessed_controls"] == 0.5
    assert counts["alert_precision_in_this_sample"] == 0.5
    assert counts["lead_days_of_hits"] == [62]


@pytest.mark.parametrize(
    "mutation",
    [
        "development_leak",
        "duplicate_company",
        "early_event",
        "censored_control",
        "changed_analysis",
        "wrong_version",
        "path_escape",
    ],
)
def test_invalid_study_cannot_claim_clean_test_results(settings, tmp_path, mutation):
    row = case(tmp_path, settings, "one", event=True)
    rows = [row]
    development = []
    if mutation == "development_leak":
        development = ["one"]
    elif mutation == "duplicate_company":
        rows.append(dict(row, split="development"))
    elif mutation == "early_event":
        row["event_date"] = "2025-03-30"
    elif mutation == "censored_control":
        row.update(target_event_observed=False, event_date=None, followup_end="2025-04-01")
    elif mutation == "changed_analysis":
        p = tmp_path / row["analysis"]
        content = json.loads(p.read_text())
        content["company"] = "tampered"
        p.write_text(json.dumps(content))
    elif mutation == "wrong_version":
        p = tmp_path / row["assessment"]
        content = json.loads(p.read_text())
        content["rule_version"] = "older-version"
        p.write_text(json.dumps(content))
    else:
        row["analysis"] = "../outside.json"
    with pytest.raises(ValueError):
        evaluate_study(manifest(tmp_path, rows, development=development))


def test_cli_evaluation_needs_no_database_settings_or_model(
    settings, tmp_path, monkeypatch, capsys
):
    from bilanco.config import Settings

    def forbidden():
        raise AssertionError("Offline evaluation must not load DB/model configuration")

    row = case(tmp_path, settings, "one", event=True, alert=True)
    path = manifest(tmp_path, [row])
    monkeypatch.setattr(Settings, "load", forbidden)
    output = tmp_path / "result.json"
    assert main(["evaluate-study", "--manifest", str(path), "--output", str(output)]) == 0
    assert (
        json.loads(output.read_text())["results"]["test"]["investor_review"]["events_flagged"] == 1
    )
    assert main(["evaluate-study", "--manifest", str(path), "--output", str(output)]) == 2
    assert "zaten var" in capsys.readouterr().err
