"""Synthetic source dates/entities and controlled model failures; no live finance."""

from dataclasses import replace
from datetime import date

import pytest
from test_document_comparisons import neutral
from test_equity import EmptyAI, EquityMemoryStore, dataset, pdf, report_text
from test_equity_review_v2 import healthy_snapshot

from bilanco.ai import AIError
from bilanco.ai_routing import RoutedCodex
from bilanco.equity_discovery import (
    SourceProposal,
    TurkeyDiscovery,
    accept_proposal,
    discover_sources,
    kap_id,
)
from bilanco.equity_models import COMPANIES, TextExtraction
from bilanco.equity_pipeline import run_equity
from bilanco.equity_text import extract_packet


@pytest.mark.parametrize(
    "url",
    [
        "https://www.kap.org.tr.evil.test/tr/Bildirim/123",
        "https://user@www.kap.org.tr/tr/Bildirim/123",
        "http://www.kap.org.tr/tr/Bildirim/123",
        "https://www.kap.org.tr/tr/Bildirim/123?next=evil",
        "https://www.kap.org.tr/tr/Bildirim/123#old",
        "https://www.kap.org.tr/tr/Bildirim/123/extra",
        "https://www.kap.org.tr:444/tr/Bildirim/123",
    ],
)
def test_untrusted_discovery_urls_rejected(url):
    with pytest.raises(ValueError):
        kap_id(url)


def test_fund_identity_requires_own_cover_and_historical_date(settings):
    company = COMPANIES["ozatd"]
    proposal = SourceProposal(
        url="https://www.kap.org.tr/tr/Bildirim/123",
        target="ABC",
        entity_name="Sentetik Ornek Portfoy Birinci Fon",
    )
    text = report_text().replace(
        "OZATA DENIZCILIK SANAYI VE TICARET A.S.", "Sentetik Ornek Portfoy Birinci Fon\nABC"
    )
    source, _, _ = accept_proposal(
        pdf(text), proposal, company, ["ABC"], date(2025, 3, 31), settings, 123
    )
    assert source.role == "related_fund"
    assert source.entity_code == "ABC"
    assert source.kind == "fund_disclosure"
    with pytest.raises(ValueError, match="future_publication"):
        accept_proposal(
            pdf(text.replace("03.03.2025", "03.04.2025")),
            proposal,
            company,
            ["ABC"],
            date(2025, 3, 31),
            settings,
            123,
        )
    with pytest.raises(ValueError, match="kapak kodu"):
        accept_proposal(
            pdf(text.replace("\nABC\n", "\nPortfoyde ABC paylari\n")),
            proposal,
            company,
            ["ABC"],
            date(2025, 3, 31),
            settings,
            123,
        )
    with pytest.raises(ValueError, match="kanıtlanmadı"):
        accept_proposal(pdf(text), proposal, company, [], date(2025, 3, 31), settings, 123)


def test_discovery_rejects_future_and_duplicate_without_ingesting_search_text(settings):
    a = healthy_snapshot(settings)
    notification = a.sources[0].disclosure_id

    class SearchAI:
        def ask(self, task, packet, schema, *, discovery):
            assert discovery and schema is TurkeyDiscovery
            assert packet["as_of"] == str(a.as_of)
            return TurkeyDiscovery(
                sources=[
                    SourceProposal(
                        url=f"https://www.kap.org.tr/tr/Bildirim/{notification}",
                        target="issuer",
                        entity_name=a.company,
                    ),
                    SourceProposal(
                        url="https://www.kap.org.tr/tr/Bildirim/999",
                        target="issuer",
                        entity_name=a.company,
                    ),
                    SourceProposal(
                        url="https://evil.test/facts", target="issuer", entity_name=a.company
                    ),
                ]
            )

    class HTTP:
        calls = []

        def request(self, url):
            self.calls.append(url)
            return pdf(report_text(published="01.04.2025 12:00:00", index=999))

    http = HTTP()
    data, audit = discover_sources(SearchAI(), settings, COMPANIES["ozatd"], a, http=http)
    assert not data.sources and not data.blocks
    assert [r["status"] for r in audit["proposals"]] == ["duplicate", "rejected", "rejected"]
    assert "future_publication" in audit["proposals"][1]["reason"]
    assert len(http.calls) == 1


def test_single_shared_budget_and_strong_retry(settings, tmp_path):
    class Fake:
        def __init__(self, settings, directory):
            self.settings, self.calls, self.receipts = settings, 0, []

        def ask(self, *args, **kwargs):
            self.calls += 1
            if self.settings.codex_model == "light":
                raise AIError("malformed JSON")
            return "valid"

    router = RoutedCodex(
        replace(settings, codex_model="light", max_ai_calls=2), tmp_path, "strong", factory=Fake
    )
    assert router.ask("test", {}, TextExtraction) == "valid"
    assert router.calls == 2
    assert router.routes[-1]["reason"] == "primary_call_failed"
    with pytest.raises(AIError, match="bütçesi"):
        router.ask("test", {}, TextExtraction)
    assert router.calls == 2


def test_grounding_error_escalates_same_packet_and_caches_selected_model(settings, tmp_path):
    a = healthy_snapshot(settings)
    obj, block, source = neutral(a, "proceeds_plan", "100")
    bad = obj.model_copy(update={"value_text": "999999"})
    packets = []

    class Fake:
        def __init__(self, settings, directory):
            self.settings, self.calls, self.receipts = settings, 0, []

        def ask(self, task, packet, schema, *, discovery):
            assert discovery is False
            self.calls += 1
            packets.append(packet)
            return TextExtraction(
                claims=[],
                forecasts=[],
                holdings=[],
                document_facts=[bad if self.settings.codex_model == "light" else obj],
            )

    settings = replace(settings, codex_model="light", max_ai_calls=2)
    ai = RoutedCodex(settings, tmp_path, "strong", factory=Fake)
    record = {}
    result = extract_packet(ai, settings, source, [block], source.entity_name, record=record)
    assert result[6] == [obj]
    assert not result[3]
    assert ai.calls == 2 and packets[0] == packets[1]
    assert record["fallback_selected"] and record["model"] == "strong"
    assert record["primary_validation_rejections"]
    cached = extract_packet(ai, settings, source, [block], source.entity_name)
    assert cached[-1] is True and ai.calls == 2


def test_packet_limit_counts_cache_and_skips_are_not_failed(settings):
    data = dataset(settings)
    ai = EmptyAI()
    first, _ = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=data,
        codex=ai,
        max_packets=1,
    )
    second, _ = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=data,
        codex=ai,
        max_packets=1,
    )
    assert first.ai["packets_processed"] == second.ai["packets_processed"] == 1
    assert second.ai["cache_hits"] == 1
    assert all(
        r["status"] in {"processed", "skipped_packet_limit"} for r in second.ai["packet_manifest"]
    )


def test_resume_keeps_legacy_cache_but_checks_company_date_and_source_hash(settings):
    class Store(EquityMemoryStore):
        def load_equity(self, run_id):
            return self.runs[run_id]

    store = Store()
    first, _ = run_equity(
        settings,
        store,
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=dataset(settings),
        codex=EmptyAI(),
        max_packets=1,
    )
    ai = EmptyAI()
    second, _ = run_equity(
        replace(settings, codex_model="light"),
        store,
        company_id="ozatd",
        as_of=first.as_of,
        resume_run=first.run_id,
        codex=ai,
        max_packets=1,
    )
    assert second.ai["cache_hits"] == 1 and ai.calls == 0
    assert second.run_id != first.run_id
    with pytest.raises(ValueError, match="aynı olmalı"):
        run_equity(
            settings, store, company_id="ozatd", as_of=date(2025, 3, 30), resume_run=first.run_id
        )
    source = first.sources[0]
    (settings.data_dir / source.path).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="özeti"):
        run_equity(settings, store, company_id="ozatd", as_of=first.as_of, resume_run=first.run_id)


def test_cached_packet_route_does_not_inherit_previous_packets_model(settings, tmp_path):
    class Fake:
        def __init__(self, settings, directory):
            self.settings, self.calls, self.receipts = settings, 0, []

        def ask(self, *args, **kwargs):
            self.calls += 1
            return TextExtraction(claims=[], forecasts=[], holdings=[])

    ai = RoutedCodex(replace(settings, codex_model="light"), tmp_path, "strong", factory=Fake)
    ai.last_model = "strong"
    assert ai.escalate("cached", {}, TextExtraction, from_model="light") is not None
    assert ai.calls == 1


def test_empty_web_result_gets_one_explicit_coverage_retry(settings, tmp_path):
    class Fake:
        def __init__(self, settings, directory):
            self.settings, self.calls, self.receipts = settings, 0, []

        def ask(self, task, packet, schema, *, discovery):
            assert discovery
            self.calls += 1
            return TurkeyDiscovery(sources=[])

    ai = RoutedCodex(replace(settings, codex_model="light"), tmp_path, "strong", factory=Fake)
    _, audit = discover_sources(ai, settings, COMPANIES["ozatd"], healthy_snapshot(settings))
    assert ai.calls == 2
    assert audit["coverage_retry"] == "empty_search_is_not_a_validation_error"
    assert ai.routes[-1]["reason"] == "empty_discovery_coverage_retry"


def test_discovered_source_is_processed_and_origin_recorded(settings, monkeypatch):
    from bilanco.equity_sources import Dataset

    data = dataset(settings)
    extra = dataset(settings)
    extra.sources[0] = extra.sources[0].model_copy(update={"id": "discovered-synthetic"})
    extra.blocks = [
        b.model_copy(update={"id": "discovered-" + b.id, "source_id": extra.sources[0].id})
        for b in extra.blocks
    ]
    extra.market = []
    calls = []

    def search(ai, settings, company, analysis):
        calls.append(analysis.ai)
        return Dataset(sources=extra.sources, blocks=extra.blocks), {
            "enabled": True,
            "status": "completed",
            "accepted": 1,
            "proposals": [{"status": "accepted", "source_id": extra.sources[0].id}],
        }

    monkeypatch.setattr("bilanco.equity_pipeline.discover_sources", search)
    a, _ = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=data,
        codex=EmptyAI(),
        max_packets=2,
        discover=True,
    )
    assert len(calls) == 1
    assert a.ai["packets_processed"] == 2
    assert a.ai["source_origins"][extra.sources[0].id] == "ai_discovery"
    assert any(
        r["source_id"] == extra.sources[0].id and r["status"] == "processed"
        for r in a.ai["packet_manifest"]
    )
    run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=data,
        codex=EmptyAI(),
        max_packets=2,
        discover=True,
        offline=True,
    )
    assert len(calls) == 1


def test_discovered_fund_attachment_keeps_fund_role_and_parent_publication_proof(settings):
    import json

    a = healthy_snapshot(settings)
    neutral(a, "fund_position", "100", subject="ABC")
    name = "Sentetik Ornek Portfoy Birinci Fon"
    main = report_text(index=999).replace("OZATA DENIZCILIK SANAYI VE TICARET A.S.", name + "\nABC")

    class Search:
        def ask(self, *args, **kwargs):
            return TurkeyDiscovery(
                sources=[
                    SourceProposal(
                        url="https://www.kap.org.tr/tr/Bildirim/999", target="ABC", entity_name=name
                    )
                ]
            )

    class HTTP:
        def request(self, url):
            if "BildirimPdf" in url:
                return pdf(main)
            if "attachment-detail" in url:
                return json.dumps(
                    [
                        {
                            "disclosure": {
                                "disclosureBasic": {
                                    "disclosureIndex": 999,
                                    "publishDate": "03.03.2025 21:47:48",
                                }
                            },
                            "attachments": [
                                {
                                    "objId": "a" * 32,
                                    "fileName": "synthetic.pdf",
                                    "fileExtension": "pdf",
                                }
                            ],
                        }
                    ]
                ).encode()
            return pdf(main + "\nSYNTHETIC FUND ATTACHMENT ONLY")

    data, audit = discover_sources(Search(), settings, COMPANIES["ozatd"], a, http=HTTP())
    assert len(data.sources) == 2 and audit["accepted_documents"] == 2
    parent, child = data.sources
    assert child.kind == "fund_attachment" and child.role == "related_fund"
    assert parent.available_at == child.available_at
    assert "attachment-detail" in child.publication_proof
    assert audit["proposals"][0]["attachments"][0]["status"] == "accepted"


def test_no_phantom_second_strong_search_when_primary_already_failed(settings, tmp_path):
    class Fake:
        def __init__(self, settings, directory):
            self.settings, self.calls, self.receipts = settings, 0, []

        def ask(self, *args, **kwargs):
            self.calls += 1
            if self.settings.codex_model == "light":
                raise AIError("unavailable")
            return TurkeyDiscovery(sources=[])

    ai = RoutedCodex(replace(settings, codex_model="light"), tmp_path, "strong", factory=Fake)
    _, audit = discover_sources(ai, settings, COMPANIES["ozatd"], healthy_snapshot(settings))
    assert ai.calls == 2
    assert "coverage_retry" not in audit
