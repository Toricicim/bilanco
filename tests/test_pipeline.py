import json

import httpx
from conftest import FakeCodex, synthetic_filing

from bilanco.acquisition import Acquirer
from bilanco.ai import AIError
from bilanco.models import Candidate, Discovery, DiscoveryCandidate, Extraction
from bilanco.pipeline import run_analysis


def test_full_synthetic_run_exports_json_markdown_and_timings(settings, memory_store, acquirer):
    result = run_analysis(settings, memory_store, acquirer=acquirer, codex=FakeCodex())
    assert result.status == "complete"
    assert result.facts and result.metrics
    directory = settings.data_dir / "runs" / result.run_id
    exported = json.loads((directory / "analysis.json").read_text())
    assert exported["schema_version"] == "1.0"
    assert isinstance(exported["facts"][0]["value"], str)  # exact decimals, no IEEE float loss
    assert exported["timings"]["source_acquisition"] >= 0
    assert (directory / "report.md").is_file()
    assert not list(directory.glob("*.html"))
    assert memory_store.runs[result.run_id]["status"] == "complete"


def test_ai_failure_keeps_python_results(settings, memory_store, acquirer):
    result = run_analysis(
        settings,
        memory_store,
        acquirer=acquirer,
        codex=FakeCodex(error=AIError("Synthetic unavailable model")),
    )
    assert result.status == "partial"
    assert result.facts and result.metrics
    assert any("AI çıkarımı" in issue for issue in result.limitations)


def test_no_source_cannot_become_safe_result(settings, memory_store):
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(403))) as client:
        acquirer = Acquirer(settings, memory_store, client=client)
        result = run_analysis(settings, memory_store, acquirer=acquirer, codex=FakeCodex())
    assert result.status == "failed" and not result.facts
    assert result.overall == "yetersiz_veri"
    assert not any("PDF" in source.url for source in result.sources)


def test_rerun_keeps_previous_output_and_deduplicates_raw_files(settings, memory_store, acquirer):
    first = run_analysis(settings, memory_store, acquirer=acquirer, codex=FakeCodex())
    previous = (settings.data_dir / "runs" / first.run_id / "analysis.json").read_bytes()
    second = run_analysis(settings, memory_store, acquirer=acquirer, codex=FakeCodex())
    assert first.run_id != second.run_id
    assert second.sources[0].cached
    assert len(list((settings.data_dir / "raw").iterdir())) == 1
    assert (settings.data_dir / "runs" / first.run_id / "analysis.json").read_bytes() == previous


def test_future_document_never_reaches_analysis(settings, memory_store):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, content=synthetic_filing(published="20010401"))
        )
    ) as client:
        result = run_analysis(
            settings,
            memory_store,
            acquirer=Acquirer(settings, memory_store, client=client),
            codex=FakeCodex(),
        )
    assert result.status == "failed"
    assert result.sources == [] and result.facts == []


def test_semantic_candidates_are_separate_from_computed_signals(settings, memory_store, acquirer):
    class CandidateAI(FakeCodex):
        def extract(self, blocks):
            self.calls += 1
            block = next(b for b in blocks if "A senior officer" in b.text)
            return Extraction(
                candidates=[
                    Candidate(
                        kind="executive_conflict",
                        block_id=block.id,
                        quote="A senior officer manages Counterparty A, which purchased an investment.",
                        actor="A senior officer",
                        counterparty="Counterparty A",
                    )
                ]
            )

    result = run_analysis(settings, memory_store, acquirer=acquirer, codex=CandidateAI())
    candidate = next(f for f in result.findings if f.category == "executive_conflict")
    assert candidate.status == "needs_review"
    assert not any("fraud" in f.id for f in result.findings)


def test_low_current_assets_produces_rule_signal(settings, memory_store):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, content=synthetic_filing(current="70"))
        )
    ) as client:
        result = run_analysis(
            settings,
            memory_store,
            acquirer=Acquirer(settings, memory_store, client=client),
            codex=FakeCodex(),
        )
    assert result.overall == "inceleme_isareti_var"
    assert next(f for f in result.findings if f.id == "current_ratio_1999").status == "signal"


def test_accepted_original_skips_duplicate_annual_mirrors(settings, memory_store, acquirer):
    ai = FakeCodex(
        discovery=Discovery(
            sources=[
                DiscoveryCandidate(
                    url="https://picker.uchicago.edu/Enron/EnronAnnualReport1999.pdf",
                    purpose="original_report",
                ),
                DiscoveryCandidate(
                    url="https://www.sec.gov/Archives/example-index.html",
                    purpose="filing_metadata",
                ),
            ]
        )
    )
    requests = []
    original_get = acquirer.get

    def tracked_get(url):
        requests.append(url)
        return original_get(url)

    acquirer.get = tracked_get
    result = run_analysis(settings, memory_store, acquirer=acquirer, codex=ai)
    assert result.status == "complete"
    assert len(requests) == 1 and len(result.sources) == 1
    assert result.ai["total_packages"] == 1
    assert ai.calls == 3  # one discovery, one extraction, one finding-order call
