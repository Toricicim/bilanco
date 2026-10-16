import re
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime

from .acquisition import (
    Acquirer,
    AcquisitionError,
    acquire_annual,
    allowed_url,
    index_proof,
    make_source,
    sgml_proof,
    submissions_proof,
)
from .ai import AIError, Codex, validate_candidates, validate_order
from .calculations import BASE_CONCEPTS, calculate, overall
from .config import AS_OF, PERIOD, SUBMISSIONS_URL, Settings
from .documents import extract_facts, read_document
from .models import Analysis, Block, Source
from .report import render
from .storage import Store, atomic_write, write_json

BOUNDARIES = [
    "Modelin Enron hakkındaki eğitim bilgisi silinemez; bu çalışma tamamen kör bir tarihsel tahmin testi değildir.",
    "Kaynak eşleşmesi, şirketin kendi beyanının bağımsız olarak doğru olduğunu göstermez.",
    "AI ilişki adaylarında alıntı doğrulaması ile anlam doğrulaması ayrıdır; adaylar kesinleşmiş risk veya hile tespiti sayılmaz.",
    "Bu sürümde sektör/emsal karşılaştırması, fiyat tahmini ve kalibre edilmiş risk olasılığı yok.",
]


def chunks(blocks: list[Block], max_chars: int) -> list[list[Block]]:
    result: list[list[Block]] = []
    group: list[Block] = []
    size = 0
    for block in blocks:
        if len(block.text) > max_chars:
            raise ValueError("Tek kaynak bloğu model paket sınırını aşıyor.")
        if size + len(block.text) > max_chars and group:
            result.append(group)
            group, size = [], 0
        group.append(block)
        size += len(block.text)
    if group:
        result.append(group)
    return result


def run_analysis(
    settings: Settings,
    store: Store,
    *,
    refresh: bool = False,
    progress: Callable[[str], None] = lambda _: None,
    acquirer: Acquirer | None = None,
    codex: Codex | None = None,
) -> Analysis:
    run_id = str(uuid.uuid4())
    directory = settings.data_dir / "runs" / run_id
    analysis = Analysis(
        run_id=run_id,
        company="Enron Corp.",
        as_of=AS_OF,
        status="failed",
        created_at=datetime.now(UTC),
        limitations=list(BOUNDARIES),
    )
    store.start(run_id, "enron", AS_OF)
    directory.mkdir(parents=True, exist_ok=False)
    ai = codex or Codex(settings, directory / "ai")
    http = acquirer or Acquirer(settings, store, refresh)
    start = time.perf_counter()
    issues: list[str] = []
    examined = 0

    @contextmanager
    def stage(name: str):
        store.stage(run_id, name)
        progress(name)
        write_json(
            directory / "checkpoint.json", {"run_id": run_id, "stage": name, "status": "running"}
        )
        begin = time.perf_counter()
        try:
            yield
        finally:
            analysis.timings[name] = round(time.perf_counter() - begin, 4)

    def add_document(source: Source, content: bytes) -> None:
        if any(known.sha256 == source.sha256 for known in analysis.sources):
            return
        if source.provenance == "archive_copy":
            issues.append("Arşiv kopyasının tarihsel sürümü kanıtlanmadı; analize alınmadı.")
            return
        read_start = time.perf_counter()
        blocks, read_issues = read_document(source, content)
        analysis.timings["document_reading"] = round(
            analysis.timings.get("document_reading", 0) + time.perf_counter() - read_start, 4
        )
        if not blocks:
            issues.extend(read_issues)
            return
        issues.extend(read_issues)
        analysis.sources.append(source)
        analysis.blocks.extend(blocks)

    try:
        with stage("source_acquisition"):
            acquisition_problems: list[str] = []
            annual = acquire_annual(http, AS_OF, acquisition_problems)
            if annual:
                add_document(*annual)
            # Acquisition failures remain visible even when a fallback succeeds.
            analysis.ai["acquisition_notes"] = acquisition_problems

        with stage("source_discovery"):
            initial_facts, _ = extract_facts(analysis.blocks, AS_OF)
            present = {(fact.concept, fact.period) for fact in initial_facts}
            missing = [
                f"{concept}, {year}"
                for concept in sorted(BASE_CONCEPTS)
                for year in (PERIOD.year, PERIOD.year - 1)
                if (concept, year) not in present
            ]
            missing.append(
                "Kesimden önceki ek resmî açıklamalar / ilişkili taraf ve koşullu yükümlülük kapsamı"
            )
            try:
                discovery = ai.discover(missing)
                seen_urls = {source.url for source in analysis.sources}
                for candidate in discovery.sources:
                    if candidate.purpose in {"original_report", "filing_metadata"} and any(
                        source.provenance in {"sec_original", "archive_copy"}
                        for source in analysis.sources
                    ):
                        # v1 supports one fixed annual filing. A PDF mirror or
                        # metadata for it adds no disclosure to the accepted original.
                        continue
                    if candidate.url in seen_urls:
                        continue
                    seen_urls.add(candidate.url)
                    if not allowed_url(candidate.url):
                        analysis.rejected.append(
                            {"reason": "discovery_url_not_allowed", "url": candidate.url}
                        )
                        continue
                    if candidate.purpose == "original_report" and candidate.url.lower().endswith(
                        ".pdf"
                    ):
                        analysis.rejected.append(
                            {
                                "reason": "archive_version_unverified",
                                "url": candidate.url,
                            }
                        )
                        continue
                    try:
                        download = http.get(candidate.url)
                        if candidate.purpose == "filing_metadata":
                            proof = (
                                submissions_proof(http, AS_OF)
                                if candidate.url == SUBMISSIONS_URL
                                else index_proof(download, AS_OF)
                            )
                            if not analysis.sources:
                                recovered = acquire_annual(
                                    http, AS_OF, acquisition_problems, proof_override=proof
                                )
                                if recovered:
                                    add_document(*recovered)
                        elif candidate.purpose == "original_report" and download.content.startswith(
                            b"%PDF-"
                        ):
                            analysis.rejected.append(
                                {"reason": "archive_version_unverified", "url": candidate.url}
                            )
                        else:
                            proof = sgml_proof(
                                download, AS_OF, annual=candidate.purpose == "original_report"
                            )
                            add_document(
                                make_source(
                                    download,
                                    proof,
                                    "sec_original"
                                    if candidate.purpose == "original_report"
                                    else "dated_official",
                                ),
                                download.content,
                            )
                    except AcquisitionError as exc:
                        analysis.rejected.append(
                            {
                                "reason": "source_not_historically_verified",
                                "url": candidate.url,
                                "detail": str(exc),
                            }
                        )
            except AIError as exc:
                issues.append(f"Kaynak keşfi tamamlanamadı: {exc}")

        with stage("table_extraction"):
            analysis.facts, rejected = extract_facts(analysis.blocks, AS_OF)
            analysis.rejected.extend(rejected)
            analysis.metrics, analysis.findings, missing = calculate(analysis.facts)
            issues.extend(missing)
            for year in (PERIOD.year, PERIOD.year - 1):
                if not any(f.period == year for f in analysis.facts):
                    issues.append(f"Beklenen finansal dönem eksik: {year}.")

        with stage("ai_extraction"):
            try:
                packages = chunks(analysis.blocks, settings.chunk_chars)
            except ValueError as exc:
                packages = []
                issues.append(str(exc))
            analysis.ai["total_packages"] = len(packages)
            for package_index, package in enumerate(packages, 1):
                progress(f"ai_extraction {package_index}/{len(packages)}")
                # Do not send obvious prompt injection passages to the model.
                if any(
                    re.search(
                        r"ignore (?:all |the )?(?:previous|system) instructions|<system>|reveal (?:your )?(?:secret|api key)",
                        b.text,
                        re.I,
                    )
                    for b in package
                ):
                    issues.append(
                        "Belge paketinde talimat benzeri metin var; AI çıkarımı yapılmadı."
                    )
                    continue
                try:
                    extraction = ai.extract(package)
                    findings, rejected = validate_candidates(extraction.candidates, package)
                    analysis.findings.extend(findings)
                    analysis.rejected.extend(rejected)
                    examined += 1
                except AIError as exc:
                    issues.append(f"Belge paketi AI çıkarımı tamamlanamadı: {exc}")
                    # Repeated identical failures should not burn the rest of the quota.
                    break
            analysis.ai["examined_packages"] = examined
            analysis.findings = list({f.id: f for f in analysis.findings}.values())

        with stage("narrative"):
            if analysis.findings:
                try:
                    narrative = ai.order(analysis.findings)
                    ordered = validate_order(narrative, analysis.findings)
                    lookup = {finding.id: finding for finding in analysis.findings}
                    analysis.findings = [lookup[fid] for fid in ordered]
                    analysis.ai["narrative"] = {
                        "status": "ordered_approved_findings",
                        "selection": narrative.model_dump(mode="json"),
                    }
                except AIError as exc:
                    analysis.ai["narrative"] = {"status": "unavailable"}
                    issues.append(
                        f"AI sunum sıralaması üretilemedi; Python bulguları korundu: {exc}"
                    )
            else:
                analysis.ai["narrative"] = {"status": "no_findings"}
        analysis.overall = overall(analysis.findings, issues)
        analysis.status = (
            "complete" if analysis.facts and not issues and not analysis.rejected else "partial"
        )
        if not analysis.sources:
            analysis.status = "failed"
            issues.extend(analysis.ai.get("acquisition_notes", []))
    except KeyboardInterrupt:
        analysis.ai["cancelled"] = True
        issues.append(
            "Çalışma kullanıcı tarafından kesildi. Tamamlanmış ham indirmeler önbellekte korundu."
        )
        analysis.status = "partial" if analysis.facts else "failed"
    except Exception as exc:
        # Never put full exception strings (which may contain DSN credentials)
        # into a user-facing report. The stage and exception class are enough.
        issues.append(
            f"Çalışma tamamlanamadı ({type(exc).__name__}); son aşama checkpoint dosyasında."
        )
        analysis.status = "partial" if analysis.facts else "failed"
    finally:
        if acquirer is None:
            http.close()
        analysis.limitations.extend(dict.fromkeys(issues))
        analysis.ai["calls"] = ai.calls
        analysis.ai["receipts"] = ai.receipts
        analysis.timings["total"] = round(time.perf_counter() - start, 4)
        analysis.timings["http_requests"] = round(http.request_seconds, 4)
        # File exports are atomic; a failed new run never replaces a prior report.
        write_json(directory / "analysis.json", analysis.model_dump(mode="json"))
        atomic_write(directory / "report.md", render(analysis).encode())
        store.finish(analysis)
        write_json(
            directory / "checkpoint.json",
            {"run_id": run_id, "stage": "finished", "status": analysis.status},
        )
    return analysis
