import argparse
import json
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import replace
from datetime import date
from pathlib import Path

import psycopg

from . import __version__
from .ai import AIError, Codex, validate_candidates
from .assessment import run_assessment
from .config import AS_OF, Settings
from .equity_models import COMPANIES
from .equity_pipeline import run_equity
from .equity_replay import STUDIES, run_replay, validate_study
from .equity_study import evaluate_study
from .launcher import choose_start
from .models import Block, Extraction
from .pipeline import run_analysis
from .storage import Store, write_json
from .terminal import print_equity_summary, saved_timings


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="bilanco", description="Kaynak ve tarih kontrollü şirket incelemesi"
    )
    result.add_argument("--version", action="version", version=__version__)
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("start", help="Şirket/tarih ve10/20/40paket seçimiyle etkileşimli başlat")
    analyze = sub.add_parser("analyze", help="Gerçek kaynak toplama ve Codex analizi başlatır")
    analyze.add_argument("--company", required=True, type=str.lower, choices=["enron", *COMPANIES])
    analyze.add_argument("--as-of", required=True, type=date.fromisoformat)
    analyze.add_argument("--bundle", type=Path, help="Doğrulamalı KAP PDF / piyasa CSV paketi")
    analyze.add_argument(
        "--max-packets",
        type=int,
        default=30,
        help="Türkiye: toplam işlenecek paket (önbellek dahil)",
    )
    analyze.add_argument(
        "--discover",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Türkiye: tarih/kimlik kontrollü AI kaynak keşfi",
    )
    analyze.add_argument(
        "--resume-run",
        type=uuid.UUID,
        help="Türkiye: aynı şirket/tarih kaynaklarını koruyup yeni koşu aç",
    )
    analyze.add_argument("--model", help="Türkiye: ilk çıkarım modeli (varsayılan gpt-6-luna)")
    analyze.add_argument(
        "--retry-cached",
        action="store_true",
        help="Türkiye: önbellekteki retli adaylar için de yeniden güçlü model çağır",
    )
    analyze.add_argument(
        "--fallback-model",
        default="gpt-6.1-sol",
        help="Türkiye: doğrulama hatasında tek güçlü tekrar",
    )
    analyze.add_argument(
        "--max-ai-calls",
        type=int,
        help="Türkiye: keşif ve tekrarlar dahil ortak fiziksel çağrı sınırı",
    )
    analyze.add_argument(
        "--offline",
        action="store_true",
        help="Finansal HTTP yok; yalnız verilen paket, Codex bağlantısı yine gerekir",
    )
    analyze.add_argument(
        "--refresh", action="store_true", help="Belgeleri önbellek yerine yeniden indir"
    )
    assess = sub.add_parser(
        "assess", help="Kayıtlı analizden kaynaklı inceleme öncelikleri üretir; veri indirmez"
    )
    assess.add_argument("--run-id", required=True, type=uuid.UUID)
    replay = sub.add_parser("replay", help="Aynı kurallarla aylık geçmiş değerlendirmeler")
    replay.add_argument("--company", required=True, type=str.lower, choices=list(COMPANIES))
    replay.add_argument("--study", required=True, choices=list(STUDIES))
    replay.add_argument("--bundle", type=Path)
    replay.add_argument("--refresh", action="store_true")
    replay.add_argument("--offline", action="store_true")
    sub.add_parser(
        "doctor", help="Yerel kurulum kontrolü; finansal veri indirmez veya model çağırmaz"
    )
    sub.add_parser(
        "check-ai",
        help="Yalnız yapay bir pasajla gerçek Codex bağlantısını sınar; finansal veri toplamaz",
    )
    db = sub.add_parser("db", help="Veritabanı işlemleri")
    db.add_argument("action", choices=["init"])
    sub.add_parser("runs", help="Son çalışmaların durumunu göster")
    study = sub.add_parser(
        "evaluate-study",
        help="Kayıtlı çıktılarda yakalama/yanlış alarm ölçer; HTTP, AI ve DB kullanmaz",
    )
    study.add_argument("--manifest", required=True, type=Path)
    study.add_argument("--output", required=True, type=Path)
    return result


def doctor(settings: Settings) -> int:
    checks = {
        "python": sys.version.split()[0],
        "codex": "missing",
        "database": "unavailable",
        "sec_contact_configured": bool(settings.sec_contact),
        "financial_data_downloaded": False,
        "model_called": False,
    }
    if shutil.which(settings.codex_binary):
        try:
            checks["codex"] = subprocess.run(
                [settings.codex_binary, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            ).stdout.strip()
            status = subprocess.run(
                [settings.codex_binary, "login", "status"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            checks["codex_login"] = "configured" if status.returncode == 0 else "not_configured"
        except (OSError, subprocess.SubprocessError):
            checks["codex"] = "check_failed"
    try:
        with Store(settings.database_url) as store:
            checks["database"] = "reachable"
            checks["postgres_version"] = store.connection.execute("SHOW server_version").fetchone()[
                0
            ]
    except psycopg.Error:
        pass
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return (
        0
        if checks["database"] == "reachable" and checks["codex"] not in {"missing", "check_failed"}
        else 1
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        if sys.stdin is None or not sys.stdin.isatty():
            parser().print_help()
            return 2
        argv = ["start"]
    args = parser().parse_args(argv)
    interactive = args.command == "start"
    if interactive and (sys.stdin is None or not sys.stdin.isatty()):
        print(
            "Başlangıç menüsü açık bir terminal ister. Otomasyon için analyze --company ... --as-of ... kullanın.",
            file=sys.stderr,
        )
        return 2
    if args.command == "evaluate-study":
        try:
            if args.output.exists():
                raise ValueError("Çıktı dosyası zaten var; yeni bir yol seçin.")
            result = evaluate_study(args.manifest)
            write_json(args.output, result)
            print(
                json.dumps(
                    {"results": result["results"], "output": str(args.output)},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        except (ValueError, OSError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if args.command == "replay":
        try:
            validate_study(args.company, args.study)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    try:
        settings = Settings.load()
        if args.command == "doctor":
            return doctor(settings)
        if args.command == "check-ai":
            block = Block(
                id="synthetic-block",
                source_id="synthetic",
                line_start=1,
                text="A senior officer manages Counterparty Z, which purchased an investment.",
            )
            directory = settings.data_dir / "diagnostics" / str(uuid.uuid4())
            ai = Codex(settings, directory)
            try:
                result = ai.ask(
                    "synthetic_connection_check",
                    {
                        "request": "This is invented test data, not an actual company. Return exactly one executive_conflict candidate with verbatim quote, actor and counterparty from this block. Do not search or access files.",
                        "blocks": [block.model_dump(mode="json")],
                    },
                    Extraction,
                )
                findings, rejected = validate_candidates(result.candidates, [block])
                passed = len(findings) == 1 and not rejected
                print(
                    json.dumps(
                        {
                            "passed": passed,
                            "financial_data_downloaded": False,
                            "real_model_called": True,
                            "audit": str(directory),
                            "duration_seconds": ai.receipts[0]["duration_seconds"],
                        },
                        indent=2,
                    )
                )
                return 0 if passed else 1
            except AIError as exc:
                print(
                    json.dumps(
                        {"passed": False, "error": str(exc), "audit": str(directory)},
                        ensure_ascii=False,
                    )
                )
                return 1
        if args.command == "analyze" and args.company == "enron":
            if args.bundle or args.offline:
                print("Enron akışı --bundle kullanmıyor.", file=sys.stderr)
                return 2
            if args.as_of != AS_OF:
                print("İlk sürüm yalnız 2000-03-31 tarihini destekliyor.", file=sys.stderr)
                return 2
            if not re.fullmatch(
                r"[^\s@]+@[^\s@]+\.[^\s@]+", settings.sec_contact
            ) or settings.sec_contact.endswith("@example.com"):
                print(
                    "SEC erişimi için .env dosyasında BILANCO_SEC_CONTACT alanına kendi iletişim e-postanı gir.",
                    file=sys.stderr,
                )
                return 2
        with Store(settings.database_url) as store:
            store.initialize()
            if interactive:
                try:
                    chosen = choose_start(
                        settings, store, read=input, write=lambda s: print(s, flush=True)
                    )
                except (EOFError, KeyboardInterrupt):
                    print("\nBaşlatılmadı; seçim iptal edildi.")
                    return 130
                if chosen is None:
                    return 0
                args = parser().parse_args(chosen)
            if args.command == "db":
                print("Veritabanı şeması hazır; finansal veri indirilmedi.")
                return 0
            if args.command == "runs":
                for row in store.recent_runs():
                    print(" | ".join(str(value) for value in row))
                return 0
            if args.command == "replay":
                result = run_replay(
                    settings,
                    store,
                    company_id=args.company,
                    study=args.study,
                    bundle=args.bundle,
                    refresh=args.refresh,
                    offline=args.offline,
                    progress=lambda s: print(f"[bilanco] {s}", file=sys.stderr),
                )
                directory = settings.data_dir / "replays" / result["id"]
                print(
                    json.dumps(
                        {
                            "replay_id": result["id"],
                            "status": result["status"],
                            "first_indicator_attention": result["first_indicator_attention"],
                            "replay": str(directory / "replay.json"),
                            "report": str(directory / "replay.md"),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return (
                    130
                    if result["status"] == "cancelled"
                    else 0
                    if result["status"] == "complete"
                    else 3
                )
            if args.command == "analyze" and args.company in COMPANIES:
                settings = replace(
                    settings, codex_model=args.model or settings.codex_model or "gpt-6-luna"
                )
                if args.max_ai_calls is not None:
                    if not 1 <= args.max_ai_calls <= 128:
                        raise ValueError("Çağrı sınırı 1–128 olmalı.")
                    settings = replace(settings, max_ai_calls=args.max_ai_calls)
                analysis, assessment = run_equity(
                    settings,
                    store,
                    company_id=args.company,
                    as_of=args.as_of,
                    bundle=args.bundle,
                    refresh=args.refresh,
                    offline=args.offline,
                    max_packets=args.max_packets,
                    discover=args.discover,
                    resume_run=args.resume_run,
                    fallback_model=args.fallback_model,
                    retry_cached=args.retry_cached,
                    progress=lambda s: print(f"[bilanco] {s}", file=sys.stderr),
                )
                directory = settings.data_dir / "runs" / analysis.run_id
                timings = saved_timings(directory, analysis)
                print_equity_summary(
                    analysis,
                    assessment,
                    directory,
                    timings=timings,
                    write=lambda s: print(
                        s, file=sys.stdout if interactive else sys.stderr, flush=True
                    ),
                )
                if not interactive:
                    print(
                        json.dumps(
                            {
                                "run_id": analysis.run_id,
                                "status": analysis.status,
                                "outcome": assessment.outcome,
                                "investor_review": assessment.investor_review.model_dump(
                                    mode="json"
                                )
                                if assessment.investor_review
                                else None,
                                "coverage": assessment.coverage,
                                "timings": timings,
                                "analysis": str(directory / "analysis.json"),
                                "assessment": str(directory / "assessment.json"),
                                "report": str(directory / "report.md"),
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
                return (
                    130
                    if analysis.ai.get("cancelled")
                    else {"complete": 0, "partial": 3, "failed": 1}[analysis.status]
                )
            if args.command == "assess":
                try:
                    source = store.load_analysis(str(args.run_id))
                except ValueError:
                    print("Kaynak çalışma bulunamadı veya henüz tamamlanmadı.", file=sys.stderr)
                    return 2
                assessment = run_assessment(
                    settings,
                    store,
                    source,
                    progress=lambda stage: print(f"[bilanco] {stage}", file=sys.stderr),
                )
                directory = settings.data_dir / "assessments" / assessment.id
                print(
                    json.dumps(
                        {
                            "assessment_id": assessment.id,
                            "source_run_id": source.run_id,
                            "status": assessment.status,
                            "assessment": str(directory / "assessment.json"),
                            "report": str(directory / "assessment.md"),
                            "coverage": assessment.coverage,
                            "timings": assessment.timings,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return {"complete": 0, "partial": 3, "failed": 1}[assessment.status]
            result = run_analysis(
                settings,
                store,
                refresh=args.refresh,
                progress=lambda stage: print(f"[bilanco] {stage}", file=sys.stderr),
            )
            directory = settings.data_dir / "runs" / result.run_id
            if result.ai.get("cancelled"):
                print(
                    json.dumps(
                        {
                            "run_id": result.run_id,
                            "status": result.status,
                            "cancelled": True,
                            "analysis": str(directory / "analysis.json"),
                            "report": str(directory / "report.md"),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return 130
            assessment_output = None
            assessment_incomplete = False
            if result.status != "failed" and result.sources:
                try:
                    assessment = run_assessment(
                        settings,
                        store,
                        result,
                        remaining_calls=max(0, settings.max_ai_calls - result.ai.get("calls", 0)),
                        progress=lambda stage: print(f"[bilanco] {stage}", file=sys.stderr),
                    )
                    target = settings.data_dir / "assessments" / assessment.id
                    assessment_output = {
                        "id": assessment.id,
                        "status": assessment.status,
                        "assessment": str(target / "assessment.json"),
                        "report": str(target / "assessment.md"),
                    }
                    assessment_incomplete = assessment.status != "complete"
                except (OSError, ValueError, psycopg.Error):
                    print(
                        "[bilanco] Öncelik raporu kaydedilemedi; kaynak analiz dosyaları korundu.",
                        file=sys.stderr,
                    )
                    assessment_incomplete = True
            if result.status == "failed":
                for reason in result.ai.get("acquisition_notes", [])[:3]:
                    print(f"[bilanco] {reason}", file=sys.stderr)
            print(
                json.dumps(
                    {
                        "run_id": result.run_id,
                        "status": result.status,
                        "analysis": str(directory / "analysis.json"),
                        "report": str(directory / "report.md"),
                        "timings": result.timings,
                        "assessment": assessment_output,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return (
                3
                if result.status == "complete" and assessment_incomplete
                else {"complete": 0, "partial": 3, "failed": 1}[result.status]
            )
    except psycopg.Error:
        print(
            "PostgreSQL bağlantısı/işlemi başarısız. DATABASE_URL ve veritabanını kontrol et; bağlantı bilgileri yazdırılmadı.",
            file=sys.stderr,
        )
        return 1
    except (ValueError, OSError) as exc:
        print(f"Yerel yapılandırma/dosya hatası ({type(exc).__name__}).", file=sys.stderr)
        return 2
