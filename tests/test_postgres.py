import os
from decimal import Decimal

import httpx
import psycopg
import pytest
from conftest import FakeCodex, synthetic_filing
from psycopg.conninfo import conninfo_to_dict

from bilanco.acquisition import Acquirer
from bilanco.config import FILING_URL
from bilanco.pipeline import run_analysis
from bilanco.storage import Store


@pytest.fixture
def postgres():
    dsn = os.environ.get("BILANCO_TEST_DATABASE_URL", "")
    if not dsn:
        pytest.skip("Set BILANCO_TEST_DATABASE_URL to an isolated test DB.")
    database = conninfo_to_dict(dsn).get("dbname", "")
    if not database.startswith("bilanco_test_"):
        pytest.fail("Refusing to touch a non-test database")
    with Store(dsn) as store:
        store.initialize()
        yield store


@pytest.mark.postgres
def test_real_database_round_trip_and_idempotent_finalization(settings, postgres):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200 if str(request.url) == FILING_URL else 404, content=synthetic_filing()
            )
        )
    ) as client:
        acquirer = Acquirer(settings, postgres, client=client)
        first = run_analysis(settings, postgres, acquirer=acquirer, codex=FakeCodex())
        assert first.status == "complete"
        postgres.finish(first)  # A retry cannot duplicate facts or sources.
        count = postgres.connection.execute(
            "SELECT count(*) FROM bilanco.facts WHERE run_id=%s", (first.run_id,)
        ).fetchone()[0]
        assert count == len(first.facts)
        number = postgres.connection.execute(
            "SELECT value FROM bilanco.facts WHERE run_id=%s AND concept='current_assets' AND period=1999",
            (first.run_id,),
        ).fetchone()[0]
        assert number == Decimal(200) and isinstance(number, Decimal)
        second = run_analysis(settings, postgres, acquirer=acquirer, codex=FakeCodex())
        assert second.sources[0].cached
        assert (
            postgres.connection.execute("SELECT count(*) FROM bilanco.downloads").fetchone()[0] == 1
        )
        assert len(postgres.recent_runs()) >= 2


@pytest.mark.postgres
def test_database_does_not_accept_dangling_evidence(postgres):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        postgres.connection.execute(
            "INSERT INTO bilanco.facts VALUES (%s,'bad','cash',1999,1,'dollars',1,'unknown','{}')",
            ("00000000-0000-0000-0000-000000000000",),
        )


@pytest.mark.postgres
def test_assessment_migration_and_immutable_source(settings, postgres, monkeypatch):
    from bilanco.assessment import run_assessment

    class NoModel:
        calls = 0
        receipts = []

        def assess_relations(self, _):
            pytest.fail("No relation candidates in this synthetic filing")

    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=synthetic_filing()))
    ) as client:
        source = run_analysis(
            settings,
            postgres,
            acquirer=Acquirer(settings, postgres, client=client),
            codex=FakeCodex(),
        )
    saved = postgres.load_analysis(source.run_id).model_dump_json()
    postgres.initialize()
    postgres.initialize()
    assert (
        postgres.connection.execute("SELECT max(version) FROM bilanco.migrations").fetchone()[0]
        == 3
    )
    result = run_assessment(settings, postgres, source, codex=NoModel())
    postgres.finish_assessment(result)
    assert (
        postgres.connection.execute(
            "SELECT count(*) FROM bilanco.assessments WHERE id=%s", (result.id,)
        ).fetchone()[0]
        == 1
    )
    payload = postgres.connection.execute(
        "SELECT payload FROM bilanco.assessments WHERE id=%s", (result.id,)
    ).fetchone()[0]
    assert payload["source_run_id"] == source.run_id
    assert postgres.load_analysis(source.run_id).model_dump_json() == saved
    changed = result.model_copy(update={"source_analysis_sha256": "f" * 64})
    with pytest.raises(ValueError, match="eşleşmedi"):
        postgres.finish_assessment(changed)


@pytest.mark.postgres
def test_equity_migration_and_roundtrip_preserve_enron(settings, postgres):
    from datetime import date

    from test_equity import EmptyAI, dataset

    from bilanco.equity_pipeline import run_equity

    before = postgres.connection.execute("SELECT count(*) FROM bilanco.facts").fetchone()[0]
    analysis, assessment = run_equity(
        settings,
        postgres,
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=dataset(settings),
        codex=EmptyAI(),
    )
    postgres.finish_equity(analysis, assessment)
    loaded_analysis, loaded_assessment = postgres.load_equity(analysis.run_id)
    assert loaded_analysis == analysis and loaded_assessment == assessment
    assert postgres.connection.execute("SELECT count(*) FROM bilanco.facts").fetchone()[0] == before
    changed = assessment.model_copy(update={"outcome": "yetersiz_veri"})
    with pytest.raises(ValueError, match="değiştirilemez"):
        postgres.finish_equity(analysis, changed)
