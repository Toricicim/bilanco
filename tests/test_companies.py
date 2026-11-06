"""Synthetic issuer registration and generic analysis; no real HTTP/model calls."""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from test_equity import EmptyAI, EquityMemoryStore, pdf, report_text

from bilanco.cli import main
from bilanco.companies import (
    CompanyError,
    all_companies,
    get_company,
    metadata_identity,
    register_company,
)
from bilanco.equity_pipeline import run_equity
from bilanco.equity_sources import Dataset, accept_kap

NAME = "ORNEK DENIZ TASIMACILIK A.S."
MEMBER = "c" * 32
URL = "https://www.kap.org.tr/tr/Bildirim/123"


class IdentityHTTP:
    def __init__(
        self, *, name=NAME, code="SYNT", member=MEMBER, index=123, pdf_name=NAME, pdf_index=123
    ):
        self.raw = json.dumps(
            [
                {
                    "disclosure": {
                        "disclosureBasic": {
                            "disclosureIndex": index,
                            "companyTitle": name,
                            "stockCode": code,
                            "mkkMemberOid": member,
                        }
                    },
                    "disclosureBody": "LATER EVENT MUST NEVER ENTER HISTORICAL ANALYSIS",
                }
            ]
        ).encode()
        self.pdf = pdf(
            f"SYNTHETIC IDENTITY ONLY\n{pdf_name}\nKAP'ta yayinlanma tarihi ve saati: 06.11.2026 08:00:00\nhttps://www.kap.org.tr/tr/Bildirim/{pdf_index}"
        )
        self.requests = []

    def request(self, url):
        self.requests.append(url)
        if "attachment-detail" in url:
            return self.raw
        if "BildirimPdf" in url:
            return self.pdf
        pytest.fail("Unexpected identity request")


def registered(settings, **kwargs):
    http = IdentityHTTP(**kwargs)
    return register_company(settings, "SYNT", URL, http=http), http


def test_registration_derives_identity_from_metadata_and_own_pdf_then_reuses_without_http(settings):
    record, http = registered(settings)
    assert len(http.requests) == 2
    assert record.company.name == NAME and record.company.kap_member == MEMBER
    assert record.company.listed_at is None  # Never invent an IPO date.
    company = get_company(settings, "synt")
    assert company == record.company
    assert len(http.requests) == 2
    assert "synt" in all_companies(settings)
    assert get_company(settings, "OZATD").ticker == "OZATD"
    assert get_company(settings, "HATSN").listed_at is not None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"code": "OTHER"},
        {"code": "XSYNTX"},
        {"index": 456},
        {"member": "bad"},
        {"name": "too short"},
        {"pdf_name": "COMPLETELY DIFFERENT COMPANY A.S."},
        {"pdf_index": 456},
    ],
)
def test_wrong_ticker_metadata_or_pdf_cannot_create_company(settings, kwargs):
    with pytest.raises(ValueError):
        registered(settings, **kwargs)
    assert not (settings.data_dir / "companies/synt.json").exists()


@pytest.mark.parametrize(
    "url",
    [
        "https://example.invalid/tr/Bildirim/123",
        "http://www.kap.org.tr/tr/Bildirim/123",
        "https://www.kap.org.tr.evil.invalid/tr/Bildirim/123",
        "https://www.kap.org.tr/tr/Bildirim/123?other=456",
        "https://user@www.kap.org.tr/tr/Bildirim/123",
        "https://www.kap.org.tr/tr/Bildirim/123#456",
    ],
)
def test_untrusted_url_rejected_before_http(settings, url):
    http = IdentityHTTP()
    with pytest.raises(ValueError):
        register_company(settings, "SYNT", url, http=http)
    assert not http.requests


@pytest.mark.parametrize("raw", [b"{}", b"[null]", b"[]", b"invalid", b"[{},{}]"])
def test_malformed_metadata_does_not_produce_identity(raw):
    with pytest.raises(CompanyError):
        metadata_identity(raw, 123, "SYNT")


def test_registry_rejects_tampering_missing_proof_and_reassignment(settings):
    record, _ = registered(settings)
    path = settings.data_dir / "companies/synt.json"
    original = path.read_bytes()
    raw = json.loads(original)
    raw["company"]["kap_member"] = "d" * 32
    path.write_text(json.dumps(raw))
    with pytest.raises(CompanyError):
        get_company(settings, "SYNT")
    path.write_bytes(original)
    with pytest.raises(CompanyError):
        registered(settings, member="e" * 32)
    assert path.read_bytes() == original
    (settings.data_dir / "raw" / record.metadata_sha256).write_bytes(b"changed")
    with pytest.raises(CompanyError):
        get_company(settings, "SYNT")


def test_unknown_ticker_and_invalid_path_do_not_trigger_discovery(settings):
    with pytest.raises(CompanyError, match="kayıtlı değil"):
        get_company(settings, "SYNT")
    with pytest.raises(CompanyError):
        get_company(settings, "../../bad")
    http = IdentityHTTP()
    with pytest.raises(CompanyError):
        register_company(settings, "OZATD", URL, http=http)
    assert not http.requests


def test_new_issuer_uses_same_pipeline_and_later_identity_is_not_historical_evidence(settings):
    registered(settings)
    company = get_company(settings, "SYNT")
    text = report_text().replace("OZATA DENIZCILIK SANAYI VE TICARET A.S.", NAME)
    source, blocks, _ = accept_kap(pdf(text), 123, company, date(2025, 3, 31), settings)
    ai = EmptyAI()
    analysis, assessment = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="synt",
        as_of=date(2025, 3, 31),
        dataset=Dataset(sources=[source], blocks=blocks),
        codex=ai,
    )
    assert analysis.company == NAME and analysis.company_id == "synt"
    assert analysis.facts and analysis.metrics and assessment.findings
    assert analysis.ai["company_identity"]["ticker"] == "SYNT"
    assert analysis.ai["company_identity"]["listed_at"] is None
    assert any("İlk işlem tarihi" in s for s in analysis.limitations)
    assert all(s.published_at.year == 2025 for s in analysis.sources)
    assert all("LATER EVENT" not in json.dumps(p) for p in ai.packets)
    assert all("IDENTITY ONLY" not in json.dumps(p) for p in ai.packets)


def test_company_commands_do_not_open_database_or_model(settings, monkeypatch, capsys):
    monkeypatch.setattr("bilanco.cli.Settings.load", lambda: settings)
    monkeypatch.setattr("bilanco.cli.Store", lambda *_: pytest.fail("DB must not open"))
    assert main(["company", "list"]) == 0
    assert {x["ticker"] for x in json.loads(capsys.readouterr().out)} == {"OZATD", "HATSN", "KERVN"}
    assert main(["company", "show", "--ticker", "SYNT"]) == 2
    assert "kayıtlı değil" in capsys.readouterr().err
    registered(settings)
    assert main(["company", "show", "--ticker", "SYNT"]) == 0
    assert json.loads(capsys.readouterr().out)["name"] == NAME


def test_generic_analyze_cli_routes_to_equity_pipeline(settings, monkeypatch, capsys):
    registered(settings)
    monkeypatch.setattr("bilanco.cli.Settings.load", lambda: settings)
    monkeypatch.setattr("bilanco.cli.Store", lambda *_: EquityMemoryStore())
    company = get_company(settings, "SYNT")
    text = report_text().replace("OZATA DENIZCILIK SANAYI VE TICARET A.S.", NAME)
    source, blocks, _ = accept_kap(pdf(text), 123, company, date(2025, 3, 31), settings)
    seen = []

    def run(config, store, **kwargs):
        seen.append(kwargs["company_id"])
        return run_equity(
            config,
            store,
            **kwargs,
            dataset=Dataset(sources=[source], blocks=blocks),
            codex=EmptyAI(),
        )

    monkeypatch.setattr("bilanco.cli.run_equity", run)
    assert main(["analyze", "--company", "SYNT", "--as-of", "2025-03-31", "--no-discover"]) == 3
    result = json.loads(capsys.readouterr().out)
    assert seen == ["synt"] and result["run_id"]


def test_skill_helper_is_portable_and_forwards_arguments_without_shell_interpolation(tmp_path):
    root = Path(__file__).resolve().parents[1]
    helper = root / ".agents/skills/bilanco/scripts/bilanco.py"
    result = subprocess.run(
        [sys.executable, str(helper), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0 and "company" in result.stdout


def test_registered_company_appears_in_terminal_menu(settings):
    from bilanco.launcher import choose_start

    class NoHistory:
        def find_equity_run(self, *args, **kwargs):
            return None

    registered(settings)
    answers = iter(["4", "2025-03-31", "1"])
    output = []
    args = choose_start(settings, NoHistory(), read=lambda _: next(answers), write=output.append)
    assert args[args.index("--company") + 1] == "synt"
    assert any(NAME in line for line in output)


def test_identity_lookup_does_not_rewrite_proof_files(settings):
    record, _ = registered(settings)
    paths = [settings.data_dir / "raw" / s for s in (record.pdf_sha256, record.metadata_sha256)]
    times = [p.stat().st_mtime_ns for p in paths]
    get_company(settings, "SYNT")
    assert [p.stat().st_mtime_ns for p in paths] == times


def test_prepare_offers_budget_and_recommends_without_running_analysis(
    settings, monkeypatch, capsys
):
    monkeypatch.setattr("bilanco.cli.Settings.load", lambda: settings)

    class NoHistory(EquityMemoryStore):
        def find_equity_run(self, *args, **kwargs):
            return None

    monkeypatch.setattr("bilanco.cli.Store", lambda *_: NoHistory())
    monkeypatch.setattr(
        "bilanco.cli.run_equity", lambda *_a, **_k: pytest.fail("No analysis before selection")
    )
    assert main(["prepare", "--company", "ozatd", "--as-of", "2025-03-31"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == "initial" and not result["analysis_started"]
    assert [o["additional_packets"] for o in result["options"]] == [10, 20, 40]
    assert [o["max_ai_calls"] for o in result["options"]] == [22, 42, 82]
    assert result["recommendation"]["choice"] == 1


def test_prepare_resume_uses_same_budget_rules_and_remaining_pool(settings):
    from bilanco.equity_models import COMPANIES
    from bilanco.launcher import prepare_review

    class Previous:
        run_id = "synthetic"
        ai = {"packets_processed": 70, "packets_planned": 141}

    class History:
        def find_equity_run(self, *args, **kwargs):
            assert kwargs["as_of"] == date(2025, 3, 31)
            return Previous(), None

    company = COMPANIES["ozatd"]
    result = prepare_review(settings, History(), company, date(2025, 3, 31))
    assert result["mode"] == "resume" and result["resume_run"] == "synthetic"
    assert [o["total_target"] for o in result["options"]] == [80, 90, 110]
    assert [o["max_ai_calls"] for o in result["options"]] == [20, 40, 80]
    Previous.ai["packets_processed"] = 138
    assert all(
        o["additional_packets"] == 3
        for o in prepare_review(settings, History(), company, date(2025, 3, 31))["options"]
    )
    Previous.ai["packets_processed"] = 141
    finished = prepare_review(settings, History(), company, date(2025, 3, 31))
    assert (
        finished["mode"] == "finished"
        and not finished["options"]
        and finished["recommendation"] is None
    )
