"""Synthetic menu/routing/output tests; no financial acquisition or real model."""

import io
import subprocess
import sys
from dataclasses import replace
from datetime import date

import pytest
from test_document_comparisons import neutral
from test_equity import EmptyAI, EquityMemoryStore, dataset
from test_equity_review_v2 import healthy_snapshot

from bilanco.ai import AIError
from bilanco.cli import main, parser
from bilanco.equity_models import TextExtraction
from bilanco.equity_pipeline import run_equity
from bilanco.equity_text import extract_packet
from bilanco.launcher import choose_start
from bilanco.terminal import duration, print_equity_summary, saved_timings


class MenuStore(EquityMemoryStore):
    def __init__(self, saved=None):
        super().__init__()
        self.saved = saved
        self.lookups = []

    def find_equity_run(self, company_id, *, as_of=None, prompt_version):
        self.lookups.append((company_id, as_of, prompt_version))
        if (
            self.saved
            and self.saved[0].company_id == company_id
            and (as_of is None or as_of == self.saved[0].as_of)
        ):
            return self.saved
        return None


def saved_result(settings, processed=30, planned=141):
    a, q = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=dataset(settings),
        codex=EmptyAI(),
    )
    a.ai.update(packets_processed=processed, packets_planned=planned)
    return a, q


def select(settings, store, answers):
    answers = iter(answers)
    output = []
    args = choose_start(settings, store, read=lambda _: next(answers), write=output.append)
    return parser().parse_args(args) if args else None, "\n".join(output)


@pytest.mark.parametrize("option,amount", [("1", 10), ("2", 20), ("3", 40)])
def test_new_run_offers_initial_packet_count(settings, option, amount):
    args, text = select(settings, MenuStore(), ["1", "2025-03-31", option])
    assert args.max_packets == amount and args.resume_run is None
    assert args.max_ai_calls == 2 * amount + 2
    assert args.discover and not args.offline
    assert "Kaç paketle başlayalım" in text


def test_resume_adds_to_previous_total_and_caps_remaining(settings):
    saved = saved_result(settings)
    args, text = select(settings, MenuStore(saved), ["1", "", "3"])
    assert args.max_packets == 70 and str(args.resume_run) == saved[0].run_id
    assert args.offline and not args.discover and not args.retry_cached
    assert args.max_ai_calls == 80
    assert "30 önceki + 40 yeni" in text
    limited = saved_result(settings, processed=138, planned=141)
    args, text = select(settings, MenuStore(limited), ["1", "", "3"])
    assert args.max_packets == 141 and args.max_ai_calls == 6
    assert "138 önceki + 3 yeni" in text


def test_changed_date_does_not_resume_other_date(settings):
    store = MenuStore(saved_result(settings))
    args, _ = select(settings, store, ["1", "2025-03-30", "1"])
    assert args.resume_run is None and args.max_packets == 10
    assert store.lookups[-1][1] == date(2025, 3, 30)


def test_complete_pool_shows_saved_result_without_new_run(settings):
    args, text = select(settings, MenuStore(saved_result(settings, 30, 30)), ["1", ""])
    assert args is None and "bütün paketler işlenmiş" in text
    assert "SONUÇ" in text


def test_invalid_selection_date_and_cancel_do_not_start_analysis(settings):
    args, text = select(
        settings, MenuStore(), ["bad", "1", "2099-01-01", "bad", "2025-03-31", "bad", "0"]
    )
    assert args is None
    assert "Geçerli seçenek" in text and "geçerli bir tarih" in text


def test_noninteractive_menu_fails_fast_before_database(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    monkeypatch.setattr("bilanco.cli.Store", lambda _: pytest.fail("No DB or prompts"))
    assert main(["start"]) == 2
    assert "açık bir terminal" in capsys.readouterr().err
    assert main([]) == 2


def test_real_process_does_not_wait_on_an_open_stdin_pipe(tmp_path):
    code = 'from bilanco.cli import main; raise SystemExit(main(["start"]))'
    process = subprocess.Popen(
        [sys.executable, "-c", code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_path,
        text=True,
    )
    try:
        assert process.wait(timeout=5) == 2  # stdin remains open, so input() would hang.
        assert "açık bir terminal" in process.stderr.read()
    finally:
        process.kill() if process.poll() is None else None
        process.communicate()


def test_interactive_main_routes_to_same_pipeline_without_json_dump(settings, monkeypatch, capsys):
    saved = saved_result(settings)
    store = MenuStore(saved)

    class TTY(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.setattr(sys, "stdin", TTY())
    answers = iter(["1", "", "2"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr("bilanco.cli.Settings.load", lambda: settings)
    monkeypatch.setattr("bilanco.cli.Store", lambda _: store)
    calls = []

    def run(*a, **kw):
        calls.append(kw)
        return saved

    monkeypatch.setattr("bilanco.cli.run_equity", run)
    assert main([]) == 3
    assert calls[0]["max_packets"] == 50 and str(calls[0]["resume_run"]) == saved[0].run_id
    out = capsys.readouterr().out
    assert "SONUÇ" in out and "SÜRELER" in out
    assert '"run_id"' not in out


@pytest.mark.parametrize("exc", [EOFError, KeyboardInterrupt])
def test_input_cancellation_does_not_call_pipeline(settings, monkeypatch, capsys, exc):
    class TTY(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.setattr(sys, "stdin", TTY())

    def cancel(_):
        raise exc

    monkeypatch.setattr("builtins.input", cancel)
    monkeypatch.setattr("bilanco.cli.Settings.load", lambda: settings)
    monkeypatch.setattr("bilanco.cli.Store", lambda _: MenuStore())
    monkeypatch.setattr(
        "bilanco.cli.run_equity", lambda *a, **kw: pytest.fail("No model/collection")
    )
    assert main(["start"]) == 130
    assert "Başlatılmadı" in capsys.readouterr().out


def test_summary_prioritizes_critical_and_preserves_counterevidence(settings):
    a, q = saved_result(settings)
    ref = q.findings[0].evidence[0]
    ordinary = q.findings[0].model_copy(
        update={"id": "context-only", "level": "context", "title": "Routine context"}
    )
    critical = q.findings[0].model_copy(
        update={
            "id": "critical",
            "level": "critical",
            "title": "Synthetic critical issue",
            "counter_evidence": [ref],
            "unknowns": ["Synthetic unknown"],
        }
    )
    review = q.findings[0].model_copy(
        update={"id": "review", "level": "review", "title": "Synthetic review"}
    )
    q.findings = [ordinary, review, critical]
    lines = []
    print_equity_summary(
        a,
        q,
        settings.data_dir / "runs" / a.run_id,
        write=lines.append,
        timings={"wall_total": 125.2},
    )
    text = "\n".join(lines)
    assert "KRİTİK İNCELEME" in text
    assert text.index("Synthetic critical issue") < text.index("Synthetic review")
    assert "Routine context" not in text
    assert ref.quote in text and "Synthetic unknown" in text
    assert "2 dk 05 sn" in text


def test_summary_unknown_is_not_safe_and_old_timings_not_invented(settings):
    a, q = saved_result(settings)
    q.findings = []
    lines = []
    print_equity_summary(
        a, q, settings.data_dir / "runs" / a.run_id, write=lines.append, timings={"total": 61}
    )
    text = "\n".join(lines)
    assert "güvenlik sonucu değildir" in text and "ölçülmedi" in text
    assert "KRİTİK İNCELEME" not in text


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0, "0 dk 00 sn"),
        (59.6, "1 dk 00 sn"),
        (125, "2 dk 05 sn"),
        (None, "ölçülmedi"),
        (-1, "ölçülmedi"),
        (float("nan"), "ölçülmedi"),
    ],
)
def test_duration(seconds, expected):
    assert duration(seconds) == expected


def test_timings_are_recorded_without_changing_immutable_analysis(settings):
    a, q = run_equity(
        settings,
        EquityMemoryStore(),
        company_id="ozatd",
        as_of=date(2025, 3, 31),
        dataset=dataset(settings),
        codex=EmptyAI(),
    )
    folder = settings.data_dir / "runs" / a.run_id
    before = (folder / "analysis.json").read_bytes()
    timings = saved_timings(folder, a)
    assert {
        "preparation",
        "acquisition",
        "table_extraction",
        "ai_extraction",
        "source_discovery",
        "rule_evaluation",
        "total",
        "persistence",
        "wall_total",
    } <= timings.keys()
    assert timings["wall_total"] >= timings["total"] >= timings["ai_extraction"]
    assert timings["source_discovery"] == 0
    assert "persistence" not in a.timings
    assert all(
        r["duration_seconds"] >= 0
        for r in a.ai["packet_manifest"]
        if r["status"].startswith("processed")
    )
    assert (folder / "analysis.json").read_bytes() == before


def test_cached_rejections_are_revalidated_without_repeated_paid_escalation(settings):
    a = healthy_snapshot(settings)
    obj, block, source = neutral(a, "proceeds_plan", "100")
    bad = obj.model_copy(update={"value_text": "999999"})

    class AI(EmptyAI):
        last_model = "light"
        retries = 0

        def ask(self, *args, **kwargs):
            self.calls += 1
            return TextExtraction(claims=[], forecasts=[], holdings=[], document_facts=[bad])

        def escalate(self, *args, **kwargs):
            self.retries += 1
            raise AIError("synthetic fallback unavailable")

    ai = AI()
    settings = replace(settings, codex_model="light")
    first = extract_packet(ai, settings, source, [block], source.entity_name)
    assert first[3] and ai.retries == 1
    record = {}
    cached = extract_packet(ai, settings, source, [block], source.entity_name, record=record)
    assert cached[-1] and cached[3] and not cached[6]
    assert record["cached_rejections_retained"] == 1 and ai.retries == 1 and ai.calls == 1
    extract_packet(ai, settings, source, [block], source.entity_name, retry_cached=True)
    assert ai.retries == 2
