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


@pytest.mark.postgres
def test_neutral_facts_comparisons_and_review_queue_roundtrip(settings, postgres):
    from test_document_comparisons import neutral
    from test_equity import EmptyAI
    from test_equity_review_v2 import healthy_snapshot

    from bilanco.equity_models import TextExtraction
    from bilanco.equity_pipeline import run_equity
    from bilanco.equity_sources import Dataset

    a = healthy_snapshot(settings)
    neutral(a, "proceeds_plan", "100", sid="plan", published="2024-02-01")
    neutral(a, "proceeds_spent", "25", sid="actual")

    class NeutralAI(EmptyAI):
        def ask(self, task, packet, schema, **kwargs):
            self.calls += 1
            ids = {b["id"] for b in packet["blocks"]}
            return TextExtraction(
                claims=[],
                forecasts=[],
                holdings=[],
                document_facts=[
                    o for o in a.document_facts if all(r.block_id in ids for r in o.evidence)
                ],
            )

    result, review = run_equity(
        settings,
        postgres,
        company_id="ozatd",
        as_of=a.as_of,
        dataset=Dataset(sources=a.sources, blocks=a.blocks, market=a.market),
        codex=NeutralAI(),
    )
    saved, checked = postgres.load_equity(result.run_id)
    assert saved.document_facts == result.document_facts
    assert saved.comparisons == result.comparisons and saved.financial_history
    assert checked.investor_review.status == "inceleme_gerekli"
    assert checked.check_traces == review.check_traces


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


@pytest.mark.postgres
def test_kervn_nominal_fields_and_signal_catalog_roundtrip(settings, postgres):
    from datetime import date

    from test_equity import EmptyAI, pdf
    from test_investor_signals import old_report

    from bilanco.equity_models import COMPANIES
    from bilanco.equity_pipeline import run_equity
    from bilanco.equity_sources import Dataset, accept_kap

    source, blocks, _ = accept_kap(
        pdf(old_report()), 123, COMPANIES["kervn"], date(2016, 3, 31), settings
    )
    analysis, assessment = run_equity(
        settings,
        postgres,
        company_id="kervn",
        as_of=date(2016, 3, 31),
        dataset=Dataset(sources=[source], blocks=blocks),
        codex=EmptyAI(),
    )
    loaded, checked = postgres.load_equity(analysis.run_id)
    assert loaded == analysis and checked == assessment
    assert all(f.measurement_basis == "nominal" for f in loaded.facts)
    assert len(checked.signal_checks) == 15


@pytest.mark.postgres
def test_launcher_selects_fullest_finished_compatible_company_date(settings, postgres):
    import uuid
    from datetime import date

    from test_equity import EmptyAI, EquityMemoryStore, dataset

    from bilanco.equity_pipeline import canonical_hash, run_equity
    from bilanco.equity_text import PROMPT_VERSION

    template, assessment = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=dataset(settings),
        codex=EmptyAI(),
    )
    company = "synthetic-launcher-" + uuid.uuid4().hex

    def save(processed, day=date(2025, 3, 31), *, prompt=PROMPT_VERSION, cancelled=False):
        a = template.model_copy(deep=True)
        a.run_id = str(uuid.uuid4())
        a.company_id = company
        a.as_of = day
        a.ai.update(
            packets_processed=processed,
            packets_planned=141,
            extraction_prompt_version=prompt,
            cancelled=cancelled,
        )
        q = assessment.model_copy(
            update={
                "source_run_id": a.run_id,
                "source_analysis_sha256": canonical_hash(a),
                "as_of": day,
            }
        )
        postgres.start(a.run_id, company, day)
        postgres.finish_equity(a, q)
        return a.run_id

    fullest = save(70)
    save(10)  # Newer timestamp must not hide the fuller same-date snapshot.
    save(100, prompt="obsolete")
    save(120, cancelled=True)
    save(130, day=date(2025, 3, 30))
    assert postgres.find_equity_run(company, prompt_version=PROMPT_VERSION)[0].run_id == fullest
    assert (
        postgres.find_equity_run(company, as_of=date(2025, 3, 31), prompt_version=PROMPT_VERSION)[
            0
        ].run_id
        == fullest
    )
    assert (
        postgres.find_equity_run(company, as_of=date(2025, 3, 29), prompt_version=PROMPT_VERSION)
        is None
    )
    assert postgres.find_equity_run(company + "-other", prompt_version=PROMPT_VERSION) is None
