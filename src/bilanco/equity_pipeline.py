"""Turkey adapter; the existing Enron pipeline and output schemas remain intact."""

import json
import re
import time
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from .ai import AIError, Codex
from .ai_routing import RoutedCodex
from .equity_discovery import discover_sources
from .equity_models import COMPANIES, EquityAnalysis, EquityAssessment, cutoff
from .equity_review_trace import investor_review, review_trace
from .equity_rules import DOMAINS, evaluate
from .equity_signals import signal_checks
from .equity_sources import Dataset, acquire, fold
from .equity_tables import extract_financial
from .equity_text import PROMPT_VERSION, extract_packet
from .pipeline import chunks
from .storage import atomic_write, digest, write_json

LIMITATIONS = [
    "Eşikler pilot inceleme kurallarıdır; dolandırıcılık/çöküş olasılığı veya al-sat emri değildir.",
    "Şirket hakkındaki model eğitim bilgisi silinemez; kapalı belge paketi tam kör deney garantisi değildir.",
    "Alıntı eşleşmesi semantik doğruluğu veya şirket beyanının gerçekliğini bağımsız doğrulamaz.",
    "Tarihsel emir derinliği ve nihai sahiplik yoğunlaşması bu ücretsiz sürümde doğrulanamadı.",
    "KAP bildirim PDF'si tam dipnot ekini içermeyebilir; okunmayan ekler kapsam eksikliğidir.",
    "Piyasa değeri/çarpan için tarihli nominal fiyat ve pay sayısı eşleşmesi gerekir; düzeltilmiş fiyatla hesaplanmadı.",
]


def canonical_hash(analysis):
    return digest(
        json.dumps(analysis.model_dump(mode="json"), sort_keys=True, ensure_ascii=False).encode()
    )


def evidence_order(sources):
    """Spend the bounded text budget on current reports before old IPO exhibits."""
    parents = {s.disclosure_id: s.kind for s in sources if s.kind != "attachment"}

    def key(source):
        kind = source.kind
        if kind == "attachment" and parents.get(source.disclosure_id) == "activity":
            kind = "activity"
        priority = {
            "financial": 0,
            "financial_attachment": 0,
            "fund_disclosure": 1,
            "fund_attachment": 1,
            "activity": 2,
            "disclosure": 3,
            "attachment": 4,
            "regulatory": 5,
        }.get(kind, 6)
        return priority, -source.published_at.timestamp(), kind == "financial_attachment", source.id

    return sorted(sources, key=key)


def render(analysis: EquityAnalysis, assessment: EquityAssessment) -> str:
    lines = [
        f"# {analysis.company} — {analysis.as_of}",
        "",
        f"Sonuç: **{assessment.outcome}**",
        f"Durum: {assessment.status} | Kural: {assessment.rule_version}",
        f"İnceleme adayı: {len(assessment.review_candidate_ids)} | Kalibrasyon: {assessment.calibration_status}",
        "",
        "## İnceleme kapsamı",
        "",
        *[f"- {k}: {v}" for k, v in assessment.coverage.items()],
        "",
        "## Göstergeler",
        "",
        "| Gösterge | Değer | Formül |",
        "|---|---:|---|",
    ]
    if assessment.investor_review:
        review = assessment.investor_review
        lines[2:2] = [
            f"**Yatırım öncesi inceleme: {review.status}**",
            "",
            review.message,
            "",
            f"İncelenecek bulgu: {len(review.finding_ids)} | Eksik/kısmi kontrol: {len(review.incomplete_checks)}",
            "",
            "Genel sonuç ile inceleme kuyruğu farklıdır; yeni adaylar kalibrasyonsuzdur.",
            "",
        ]
    lines += [f"| {m.id} | {m.value:.6f} {m.unit} | {m.formula} |" for m in analysis.metrics]
    lines += ["", "## Yatırımcı gözlemleri ve veri eksikleri", ""]
    lines += ["| Kontrol | Durum | Eksik girdi |", "|---|---|---|"]
    lines += [
        f"| {c.title} | {c.status} | {'; '.join(c.missing_inputs)} |"
        for c in assessment.signal_checks
    ]
    lines += [
        "",
        "evidence_found yalnız kaynaklı kayıt bulunduğunu gösterir; usulsüzlük veya tam kontrol sonucu değildir.",
    ]
    lines += [
        "",
        "## Kontrol izleri",
        "",
        "Kaynak sayıları eldeki havuzu ve tam işlenen AI kaynaklarını gösterir; kontrolün tüm girdilerinin bulunduğu anlamına gelmez.",
        "",
        "| Kontrol | Durum | Kaynak / taranan | Kabul / ret | Ret nedenleri |",
        "|---|---|---:|---:|---|",
    ]
    lines += [
        f"| {t.title} | {t.status} | {t.sources_acquired} / {t.sources_scanned} | {t.candidates_accepted} / {t.candidates_rejected} | {'; '.join(t.rejection_reasons)} |"
        for t in assessment.check_traces
    ]
    lines += ["", "## Belgeler arası karşılaştırma", ""]
    for c in analysis.comparisons:
        lines += [
            f"- {c.id} / {c.status}: {c.explanation}",
            *[f"  - Eksik: {x}" for x in c.missing_inputs],
        ]
    lines += ["", "## Fon ve likidite izi", ""]
    for e in analysis.fund_exposures:
        lines += [
            f"- {e.code} / {e.period_end}: {e.note}",
            f"  - Kaynakta belirtilen iade: {e.redemption_days if e.redemption_days is not None else 'bilinmiyor'} / {e.redemption_day_basis}",
            *[f"  - Eksik: {x}" for x in e.missing_inputs],
        ]
    lines += [
        "",
        "## Tarihli kâr / nakit geçmişi",
        "",
        "| Dönem | Kapsam | Nakit/kâr | Kâr pozitif, nakit negatif |",
        "|---|---|---:|---|",
    ]
    lines += [
        f"| {p.period_start}–{p.period_end} | {p.scope} | {p.cash_profit if p.cash_profit is not None else 'bilinmiyor'} | {p.profit_positive_cash_negative if p.profit_positive_cash_negative is not None else 'bilinmiyor'} |"
        for p in analysis.financial_history
    ]
    lines += [
        "",
        "Birikimli çeyrekler toplanmadı; oranlar açıklanmış nakdi kullanır, düzeltilmiş nakit veya usulsüzlük değildir.",
    ]
    lines += ["", "## Bulgular", ""]
    if not assessment.findings:
        lines.append(
            "Değerlendirilebilen veride bulgu üretilemedi. Eksik veri güvenlik göstergesi değildir."
        )
    for f in assessment.findings:
        lines += [
            f"### {f.title}",
            "",
            f"{f.level} / {f.domain} / {f.rule_id}",
            "Genel sonuca dahil: "
            + ("evet" if f.contributes_to_outcome else "hayır; ayrı inceleme kaydı"),
            "",
            f.explanation,
            "",
        ]
        for ref in f.evidence:
            block = next((b for b in analysis.blocks if b.id == ref.block_id), None)
            source = next((s for s in analysis.sources if block and s.id == block.source_id), None)
            location = f"sayfa {block.page}, satır {block.line_start}" if block else ref.block_id
            lines.append(f"> {ref.quote.replace(chr(10), chr(10) + '> ')}")
            if source:
                lines += [
                    "",
                    f"[Kaynak]({source.url}) — {source.published_at.isoformat()} — {location}",
                    "",
                ]
        for ref in f.counter_evidence:
            lines += [f"Dengeleyici alıntı: {ref.quote}", ""]
        lines += [f"Bilinmeyen: {u}" for u in f.unknowns]
    lines += ["", "## Kaynaklar", ""]
    for source in analysis.sources:
        lines.append(
            f"- [{source.id}]({source.url}) — yayın: {source.published_at.isoformat()}; {source.provenance}; {source.version_note}"
        )
    lines += ["", "## Piyasa kaynakları", ""]
    for series in analysis.market:
        dates = f"{series.bars[0].day}–{series.bars[-1].day}" if series.bars else "kayıt yok"
        lines.append(
            f"- [{series.symbol}]({series.url}) — {dates}; {len(series.bars)} kayıt; {series.price_basis}; veri özeti {series.sha256}"
        )
    lines += ["", "## Sınırlar ve eksikler", "", *[f"- {x}" for x in assessment.limitations]]
    return "\n".join(lines) + "\n"


def run_equity(
    settings,
    store,
    *,
    company_id: str,
    as_of: date,
    bundle: Path | None = None,
    refresh=False,
    progress=lambda _: None,
    dataset: Dataset | None = None,
    codex=None,
    offline=False,
    max_packets=None,
    discover=False,
    resume_run=None,
    fallback_model=None,
    retry_cached=False,
):
    started = time.perf_counter()
    if max_packets is not None and not 1 <= max_packets <= 1000:
        raise ValueError("Paket sınırı 1–1000 olmalı.")
    if resume_run and (dataset is not None or bundle is not None or refresh):
        raise ValueError("Devam koşusu dataset/bundle/refresh ile birleştirilemez.")
    legacy_packets = set()
    resumed = None
    if resume_run:
        resumed, previous_assessment = store.load_equity(str(resume_run))
        if resumed.company_id != company_id or resumed.as_of != as_of:
            raise ValueError("Devam koşusunun şirketi ve kesim tarihi aynı olmalı.")
        if canonical_hash(resumed) != previous_assessment.source_analysis_sha256:
            raise ValueError("Devam kaydının özeti doğrulanamadı.")
        for source in resumed.sources:
            path = (settings.data_dir / source.path).resolve()
            if not path.is_relative_to(settings.data_dir.resolve()) or not path.is_file():
                raise ValueError("Devam kaynağı bulunamadı.")
            if (
                path.stat().st_size > settings.max_download_bytes
                or digest(path.read_bytes()) != source.sha256
            ):
                raise ValueError("Devam kaynağının özeti doğrulanamadı.")
        legacy_packets = {
            (r["source_id"], tuple(r["block_ids"]))
            for r in resumed.ai.get("packet_manifest", [])
            if r["status"] in {"processed", "processed_with_rejections"}
        }
        dataset = Dataset(
            sources=resumed.sources,
            blocks=resumed.blocks,
            market=resumed.market,
            issues=[
                x
                for v in resumed.ai.get("source_coverage", {}).values()
                for x in v.get("read_issues", [])
            ],
        )
    company = COMPANIES[company_id]
    if as_of < company.listed_at:
        raise ValueError("Bu şirket için halka arz öncesi hisse incelemesi desteklenmiyor.")
    if as_of > datetime.now(UTC).astimezone(cutoff(as_of).tzinfo).date():
        raise ValueError("Gelecek tarihli analiz yapılamaz.")
    run_id = str(uuid.uuid4())
    directory = settings.data_dir / "runs" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    analysis = EquityAnalysis(
        run_id=run_id,
        company=company.name,
        company_id=company_id,
        as_of=as_of,
        created_at=datetime.now(UTC),
        limitations=list(LIMITATIONS),
    )
    ai = codex or (
        RoutedCodex(settings, directory / "ai", fallback_model)
        if fallback_model
        else Codex(settings, directory / "ai")
    )
    if resumed:
        analysis.ai["resumed_from"] = str(resume_run)
        analysis.ai["resume_extraction_packets"] = len(legacy_packets)
    analysis.timings.update(
        preparation=round(time.perf_counter() - started, 4), ai_extraction=0.0, source_discovery=0.0
    )
    store.start(run_id, company_id, as_of)

    def stage(name):
        store.stage(run_id, name)
        progress(name)
        write_json(
            directory / "checkpoint.json", {"run_id": run_id, "stage": name, "status": "running"}
        )

    try:
        stage("tr_source_acquisition")
        begin = time.perf_counter()
        data = (
            dataset
            if dataset is not None
            else acquire(
                settings,
                company,
                as_of,
                bundle=bundle,
                refresh=refresh,
                progress=progress,
                offline=offline,
            )
        )
        analysis.sources = [s for s in data.sources if s.available_at <= cutoff(as_of)]
        allowed = {s.id for s in analysis.sources}
        analysis.blocks = [b for b in data.blocks if b.source_id in allowed]
        # A replay dataset can contain later rows; every snapshot gets a separate trimmed copy.
        for series in data.market:
            bars = [b for b in series.bars if b.day <= as_of]
            sha = digest("\n".join(b.model_dump_json() for b in bars).encode())
            analysis.market.append(series.model_copy(update={"bars": bars, "sha256": sha}))
        analysis.rejected = list(data.rejected)
        analysis.ai["acquisition_complete"] = (
            resumed.ai.get("acquisition_complete", False)
            if resumed
            else not data.rejected and not data.issues
        )
        analysis.limitations.extend(data.issues)
        analysis.limitations.extend(x for s in analysis.market for x in s.limitations)
        analysis.timings["acquisition"] = round(time.perf_counter() - begin, 4)
        stage("tr_table_extraction")
        begin = time.perf_counter()
        for source in analysis.sources:
            if source.role != "issuer":
                continue
            source_blocks = [b for b in analysis.blocks if b.source_id == source.id]
            linked_ids = {
                s.id
                for s in analysis.sources
                if source.disclosure_id is not None
                and s.disclosure_id == source.disclosure_id
                and s.id != source.id
                and s.kind in {"financial", "financial_attachment"}
            }
            facts, rejected = extract_financial(
                source,
                source_blocks,
                issuer_identity=company.identity,
                linked_blocks=[b for b in analysis.blocks if b.source_id in linked_ids],
            )
            analysis.facts.extend(facts)
            analysis.rejected.extend(rejected)
        analysis.timings["table_extraction"] = round(time.perf_counter() - begin, 4)
        stage("tr_ai_evidence_extraction")
        complete, processed, cache_hits = True, 0, 0
        manifest = []
        source_coverage = {}

        def plan(sources):
            queue = []
            for source in evidence_order(sources):
                source_blocks = [b for b in analysis.blocks if b.source_id == source.id]
                entry = {
                    "planned": 0,
                    "processed": 0,
                    "rejections": 0,
                    "failed": 0,
                    "skipped": 0,
                    "read_issues": [x for x in data.issues if source.id in x],
                }
                source_coverage[source.id] = entry
                context = [
                    b
                    for b in source_blocks
                    if company.identity in fold(b.text)
                    and re.search(r"\([\s\"“”']*Şirket[\s\"“”']*\)", b.text, re.I)
                ][:2]
                context_size = sum(len(b.text) for b in context)
                if context_size > settings.chunk_chars // 2:
                    context, context_size = [], 0
                try:
                    packets = chunks(source_blocks, settings.chunk_chars - context_size)
                except ValueError:
                    entry["failed"] += 1
                    analysis.limitations.append(
                        f"{source.id}: Kaynak bloğu AI paket sınırını aştı."
                    )
                    continue
                entry["planned"] = len(packets)
                for index, packet in enumerate(packets, 1):
                    packet = list({b.id: b for b in [*context, *packet]}.values())
                    record = {
                        "source_id": source.id,
                        "index": index,
                        "block_ids": [b.id for b in packet],
                        "status": "pending",
                    }
                    manifest.append(record)
                    queue.append((source, packet, record, entry))
            return queue

        def process(queue):
            nonlocal complete, processed, cache_hits
            for source, packet, record, entry in queue:
                if max_packets is not None and processed >= max_packets:
                    record["status"] = "skipped_packet_limit"
                    entry["skipped"] += 1
                    complete = False
                    continue
                progress(
                    f"AI {source.id}: {record['index']}/{entry['planned']} (toplam {processed})"
                )
                packet_started = time.perf_counter()
                try:
                    result = extract_packet(
                        ai,
                        settings,
                        source,
                        packet,
                        source.entity_name or company.name,
                        allow_legacy_cache=(source.id, tuple(record["block_ids"]))
                        in legacy_packets,
                        record=record,
                        retry_cached=retry_cached,
                    )
                    (
                        claims,
                        forecasts,
                        holdings,
                        rejected,
                        observations,
                        signals,
                        document_facts,
                        cached,
                    ) = result
                    for target, values in (
                        (analysis.claims, claims),
                        (analysis.forecasts, forecasts),
                        (analysis.holdings, holdings),
                        (analysis.observations, observations),
                        (analysis.signals, signals),
                        (analysis.document_facts, document_facts),
                        (analysis.rejected, rejected),
                    ):
                        target.extend(values)
                    record.update(
                        status="processed_with_rejections" if rejected else "processed",
                        cached=cached,
                        rejections=len(rejected),
                    )
                    entry["processed"] += 1
                    entry["rejections"] += len(rejected)
                    processed += 1
                    cache_hits += int(cached)
                    if rejected:
                        complete = False
                except AIError as exc:
                    record.update(status="failed", error=str(exc))
                    entry["failed"] += 1
                    complete = False
                    analysis.limitations.append(str(exc))
                finally:
                    elapsed = time.perf_counter() - packet_started
                    record["duration_seconds"] = round(elapsed, 4)
                    analysis.timings["ai_extraction"] = round(
                        analysis.timings["ai_extraction"] + elapsed, 4
                    )

        queue = plan(analysis.sources)
        seed_count = min(9, max_packets) if max_packets is not None else 9
        process(queue[:seed_count])
        if discover and not offline:
            stage("tr_ai_source_discovery")
            begin = time.perf_counter()
            extra, discovery_audit = discover_sources(ai, settings, company, analysis)
            analysis.timings["source_discovery"] = round(time.perf_counter() - begin, 4)
            analysis.ai["discovery"] = discovery_audit
            analysis.sources.extend(extra.sources)
            analysis.blocks.extend(extra.blocks)
            data.issues.extend(extra.issues)
            analysis.limitations.extend(extra.issues)
            # Related funds are evidence for fund terms, never issuer accounts.
            begin = time.perf_counter()
            for source in extra.sources:
                if source.role == "issuer":
                    facts, rejected = extract_financial(
                        source,
                        [b for b in extra.blocks if b.source_id == source.id],
                        issuer_identity=company.identity,
                    )
                    analysis.facts.extend(facts)
                    analysis.rejected.extend(rejected)
            analysis.timings["table_extraction"] = round(
                analysis.timings["table_extraction"] + time.perf_counter() - begin, 4
            )
            process(plan(extra.sources))
        else:
            analysis.ai["discovery"] = {
                "enabled": False,
                "status": "offline" if offline else "disabled",
                "proposals": [],
                "accepted": 0,
            }
        process(queue[seed_count:])
        analysis.ai["packet_limit"] = max_packets
        analysis.ai["retry_cached"] = retry_cached
        analysis.ai["model_routes"] = getattr(ai, "routes", [])
        discovered_ids = {
            sid
            for p in analysis.ai["discovery"]["proposals"]
            for sid in [
                p.get("source_id"),
                *[x.get("source_id") for x in p.get("attachments", [])],
            ]
            if sid
        }
        analysis.ai["source_origins"] = {
            s.id: (
                "ai_discovery"
                if s.id in discovered_ids
                else "resumed_acquisition"
                if resumed
                else "acquisition"
            )
            for s in analysis.sources
        }
        analysis.ai.update(
            extraction_complete=complete
            and processed > 0
            and all(
                e["planned"] == e["processed"] and not e["failed"] for e in source_coverage.values()
            ),
            scan_complete=processed > 0
            and all(
                e["planned"] == e["processed"] and not e["failed"] for e in source_coverage.values()
            ),
            packets_planned=sum(e["planned"] for e in source_coverage.values()),
            packet_manifest=manifest,
            source_coverage=source_coverage,
            packets_processed=processed,
            cache_hits=cache_hits,
            calls=ai.calls,
            receipts=ai.receipts,
            web_search=any(r.get("web_search") for r in ai.receipts),
            extraction_prompt_version=PROMPT_VERSION,
        )
    except KeyboardInterrupt:
        analysis.ai["cancelled"] = True
        analysis.limitations.append("Kullanıcı iptal etti; kalan aşamalar çalıştırılmadı.")
    except (ValueError, OSError) as exc:
        analysis.limitations.append(f"Çalışma tamamlanamadı ({type(exc).__name__}): {exc}")
    begin = time.perf_counter()
    if analysis.ai.get("cancelled"):
        findings, coverage, outcome = [], dict.fromkeys(DOMAINS, "cancelled"), "yetersiz_veri"
    else:
        analysis.metrics, findings, coverage, outcome = evaluate(analysis)
    analysis.status = (
        "partial" if analysis.sources or any(s.bars for s in analysis.market) else "failed"
    )
    # Complete means acquisition+calculation+semantic coverage; unavailable depth stays explicit.
    acquisition_issues = bool(analysis.rejected) or any(
        "alınamadı" in issue or "sınırı aşı" in issue
        for issue in analysis.limitations[len(LIMITATIONS) :]
    )
    if (
        coverage["financial"] == coverage["operations"] == "available"
        and coverage["market"].startswith("price_available")
        and analysis.ai.get("extraction_complete")
        and analysis.ai.get("acquisition_complete")
        and not acquisition_issues
    ):
        analysis.status = "complete"
    analysis.limitations = list(dict.fromkeys(analysis.limitations))
    checks = signal_checks(analysis, findings, coverage)
    traces = review_trace(analysis, findings, checks)
    review = investor_review(findings, traces)
    analysis.timings["rule_evaluation"] = round(time.perf_counter() - begin, 4)
    analysis.timings["total"] = round(time.perf_counter() - started, 4)
    assessment = EquityAssessment(
        source_run_id=run_id,
        source_analysis_sha256=canonical_hash(analysis),
        company=company.name,
        as_of=as_of,
        outcome=outcome,
        status=analysis.status,
        findings=findings,
        coverage=coverage,
        limitations=analysis.limitations,
        review_candidate_ids=[f.id for f in findings if f.level in {"review", "critical"}],
        signal_checks=checks,
        check_traces=traces,
        investor_review=review,
    )
    begin = time.perf_counter()
    write_json(directory / "analysis.json", analysis.model_dump(mode="json"))
    write_json(directory / "assessment.json", assessment.model_dump(mode="json"))
    atomic_write(directory / "report.md", render(analysis, assessment).encode())
    store.finish_equity(analysis, assessment)
    run_timings = {
        **analysis.timings,
        "persistence": round(time.perf_counter() - begin, 4),
        "wall_total": round(time.perf_counter() - started, 4),
    }
    write_json(
        directory / "checkpoint.json",
        {"run_id": run_id, "stage": "finished", "status": analysis.status, "timings": run_timings},
    )
    return analysis, assessment
