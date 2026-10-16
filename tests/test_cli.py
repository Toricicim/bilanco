import importlib
import json

from bilanco.cli import main


def test_import_never_collects_financial_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import bilanco

    importlib.reload(bilanco)
    assert not list(tmp_path.iterdir())


def test_unsupported_date_stops_before_database_or_network(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["analyze", "--company", "enron", "--as-of", "1999-04-05"]) == 2
    assert "yalnız" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_missing_contact_stops_before_collection(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BILANCO_SEC_CONTACT", raising=False)
    assert main(["analyze", "--company", "enron", "--as-of", "2000-03-31"]) == 2
    assert "BILANCO_SEC_CONTACT" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_invalid_assessment_uuid_stops_before_database(monkeypatch):
    import pytest

    monkeypatch.setattr("bilanco.cli.Store", lambda _: pytest.fail("No database expected"))
    with pytest.raises(SystemExit) as error:
        main(["assess", "--run-id", "../not-a-uuid"])
    assert error.value.code == 2


def test_missing_assessment_run_has_actionable_error(settings, memory_store, monkeypatch, capsys):
    import uuid

    monkeypatch.setattr("bilanco.cli.Settings.load", lambda: settings)
    monkeypatch.setattr("bilanco.cli.Store", lambda _: memory_store)
    assert main(["assess", "--run-id", str(uuid.uuid4())]) == 2
    assert "Kaynak çalışma bulunamadı" in capsys.readouterr().err


def test_assess_needs_no_sec_contact_and_does_not_collect(
    settings, memory_store, monkeypatch, capsys, source
):
    import uuid
    from dataclasses import replace
    from datetime import UTC, datetime

    from test_assessment import ReviewAI

    from bilanco.assessment import run_assessment
    from bilanco.config import AS_OF
    from bilanco.models import Analysis

    saved = Analysis(
        run_id=str(uuid.uuid4()),
        company="Synthetic",
        as_of=AS_OF,
        created_at=datetime.now(UTC),
        status="complete",
        sources=[source],
    )
    memory_store.finish(saved)
    monkeypatch.setattr("bilanco.cli.Settings.load", lambda: replace(settings, sec_contact=""))
    monkeypatch.setattr("bilanco.cli.Store", lambda _: memory_store)
    ai = ReviewAI()
    monkeypatch.setattr(
        "bilanco.cli.run_assessment", lambda *a, **kw: run_assessment(*a, **kw, codex=ai)
    )
    assert main(["assess", "--run-id", saved.run_id]) == 0
    assert ai.calls == 0
    assert json.loads(capsys.readouterr().out)["status"] == "complete"


def test_analyze_calls_assessment_with_remaining_global_budget(
    settings, memory_store, monkeypatch, capsys, source
):
    import uuid
    from datetime import UTC, datetime

    from bilanco.assessment_models import Assessment
    from bilanco.config import AS_OF
    from bilanco.models import Analysis

    saved = Analysis(
        run_id=str(uuid.uuid4()),
        company="Synthetic",
        as_of=AS_OF,
        created_at=datetime.now(UTC),
        status="complete",
        sources=[source],
        ai={"calls": 7},
    )
    remaining = []

    def assess(_settings, _store, analysis, **kwargs):
        remaining.append(kwargs["remaining_calls"])
        return Assessment(
            id=str(uuid.uuid4()),
            source_run_id=analysis.run_id,
            source_analysis_sha256="0" * 64,
            company=analysis.company,
            as_of=AS_OF,
            created_at=datetime.now(UTC),
            source_analysis_status=analysis.status,
            status="partial",
        )

    monkeypatch.setattr("bilanco.cli.Settings.load", lambda: settings)
    monkeypatch.setattr("bilanco.cli.Store", lambda _: memory_store)
    monkeypatch.setattr("bilanco.cli.run_analysis", lambda *a, **kw: saved)
    monkeypatch.setattr("bilanco.cli.run_assessment", assess)
    assert main(["analyze", "--company", "enron", "--as-of", "2000-03-31"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert remaining == [settings.max_ai_calls - 7]
    assert result["status"] == "complete" and result["assessment"]["status"] == "partial"
