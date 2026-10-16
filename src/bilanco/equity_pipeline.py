"""Turkey adapter; the existing Enron pipeline and output schemas remain intact."""

import json
import re
import time
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from .ai import AIError, Codex
from .equity_models import COMPANIES, EquityAnalysis, EquityAssessment, cutoff
from .equity_rules import DOMAINS, evaluate
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
            "financial_attachment": 1,
            "activity": 2,
            "disclosure": 3,
            "attachment": 4,
            "regulatory": 5,
        }.get(kind, 6)
        return priority, -source.published_at.timestamp(), source.id

    return sorted(sources, key=key)


def render(analysis: EquityAnalysis, assessment: EquityAssessment) -> str:
    lines = [
        f"# {analysis.company} — {analysis.as_of}",
        "",
        f"Sonuç: **{assessment.outcome}**",
        f"Durum: {assessment.status} | Kural: {assessment.rule_version}",
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
    lines += [f"| {m.id} | {m.value:.6f} {m.unit} | {m.formula} |" for m in analysis.metrics]
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
):
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
    ai = codex or Codex(settings, directory / "ai")
    started = time.perf_counter()
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
        analysis.timings["acquisition"] = round(time.perf_counter() - begin, 4)
        analysis.sources = [s for s in data.sources if s.available_at <= cutoff(as_of)]
        allowed = {s.id for s in analysis.sources}
        analysis.blocks = [b for b in data.blocks if b.source_id in allowed]
        # A replay dataset can contain later rows; every snapshot gets a separate trimmed copy.
        for series in data.market:
            bars = [b for b in series.bars if b.day <= as_of]
            sha = digest("\n".join(b.model_dump_json() for b in bars).encode())
            analysis.market.append(series.model_copy(update={"bars": bars, "sha256": sha}))
        analysis.rejected = list(data.rejected)
        analysis.limitations.extend(data.issues)
        analysis.limitations.extend(x for s in analysis.market for x in s.limitations)
        stage("tr_table_extraction")
        for source in analysis.sources:
            source_blocks = [b for b in analysis.blocks if b.source_id == source.id]
            facts, rejected = extract_financial(source, source_blocks)
            analysis.facts.extend(facts)
            analysis.rejected.extend(rejected)
        stage("tr_ai_evidence_extraction")
        complete, processed, cache_hits = True, 0, 0
        for source in evidence_order(analysis.sources):
            source_blocks = [b for b in analysis.blocks if b.source_id == source.id]
            # Carry explicit issuer alias definitions into later note packets.
            context = [
                b
                for b in source_blocks
                if company.identity in fold(b.text)
                and re.search(r"\([\s\"“”']*Şirket[\s\"“”']*\)", b.text, re.I)
            ][:2]
            context_size = sum(len(b.text) for b in context)
            if context_size > settings.chunk_chars // 2:
                context = []
                context_size = 0
            try:
                packets = chunks(source_blocks, settings.chunk_chars - context_size)
            except ValueError:
                complete = False
                analysis.limitations.append("Kaynak bloğu AI paket sınırını aştı.")
                continue
            for index, packet in enumerate(packets, 1):
                packet = list({b.id: b for b in [*context, *packet]}.values())
                progress(f"AI {source.id}: {index}/{len(packets)}")
                try:
                    claims, forecasts, holdings, rejected, cached = extract_packet(
                        ai, settings, source, packet, company.name
                    )
                    analysis.claims.extend(claims)
                    analysis.forecasts.extend(forecasts)
                    analysis.holdings.extend(holdings)
                    analysis.rejected.extend(rejected)
                    processed += 1
                    cache_hits += int(cached)
                    if rejected:
                        complete = False
                except AIError as exc:
                    complete = False
                    analysis.limitations.append(str(exc))
        analysis.ai.update(
            extraction_complete=complete and processed > 0,
            packets_processed=processed,
            cache_hits=cache_hits,
            calls=ai.calls,
            receipts=ai.receipts,
            web_search=False,
            extraction_prompt_version=PROMPT_VERSION,
        )
    except KeyboardInterrupt:
        analysis.ai["cancelled"] = True
        analysis.limitations.append("Kullanıcı iptal etti; kalan aşamalar çalıştırılmadı.")
    except (ValueError, OSError) as exc:
        analysis.limitations.append(f"Çalışma tamamlanamadı ({type(exc).__name__}): {exc}")
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
        and not acquisition_issues
    ):
        analysis.status = "complete"
    analysis.timings["total"] = round(time.perf_counter() - started, 4)
    analysis.limitations = list(dict.fromkeys(analysis.limitations))
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
    )
    write_json(directory / "analysis.json", analysis.model_dump(mode="json"))
    write_json(directory / "assessment.json", assessment.model_dump(mode="json"))
    atomic_write(directory / "report.md", render(analysis, assessment).encode())
    store.finish_equity(analysis, assessment)
    write_json(
        directory / "checkpoint.json",
        {"run_id": run_id, "stage": "finished", "status": analysis.status},
    )
    return analysis, assessment
