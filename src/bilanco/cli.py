import argparse
import json
import re
import shutil
import subprocess
import sys
import uuid
from datetime import date

import psycopg

from . import __version__
from .ai import AIError, Codex, validate_candidates
from .config import AS_OF, Settings
from .models import Block, Extraction
from .pipeline import run_analysis
from .storage import Store


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="bilanco", description="Kaynak ve tarih kontrollü şirket incelemesi"
    )
    result.add_argument("--version", action="version", version=__version__)
    sub = result.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze", help="Gerçek kaynak toplama ve Codex analizi başlatır")
    analyze.add_argument("--company", required=True, choices=["enron"])
    analyze.add_argument("--as-of", required=True, type=date.fromisoformat)
    analyze.add_argument(
        "--refresh", action="store_true", help="Belgeleri önbellek yerine yeniden indir"
    )
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
    args = parser().parse_args(argv)
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
        if args.command == "analyze":
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
            if args.command == "db":
                print("Veritabanı şeması hazır; finansal veri indirilmedi.")
                return 0
            if args.command == "runs":
                for row in store.recent_runs():
                    print(" | ".join(str(value) for value in row))
                return 0
            result = run_analysis(
                settings,
                store,
                refresh=args.refresh,
                progress=lambda stage: print(f"[bilanco] {stage}", file=sys.stderr),
            )
            directory = settings.data_dir / "runs" / result.run_id
            print(
                json.dumps(
                    {
                        "run_id": result.run_id,
                        "status": result.status,
                        "analysis": str(directory / "analysis.json"),
                        "report": str(directory / "report.md"),
                        "timings": result.timings,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return {"complete": 0, "partial": 3, "failed": 1}[result.status]
    except psycopg.Error:
        print(
            "PostgreSQL bağlantısı/işlemi başarısız. DATABASE_URL ve veritabanını kontrol et; bağlantı bilgileri yazdırılmadı.",
            file=sys.stderr,
        )
        return 1
    except (ValueError, OSError) as exc:
        print(f"Yerel yapılandırma/dosya hatası ({type(exc).__name__}).", file=sys.stderr)
        return 2
