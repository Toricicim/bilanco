import re

from .models import Analysis

STATUS = {
    "signal": "İnceleme işareti",
    "context": "Dengeleyici / bağlamsal bilgi",
    "needs_review": "Anlam doğrulaması gerekli",
    "unavailable": "Veri yok",
}


def literal(text: str) -> str:
    # Source contents cannot become executable HTML, images or Markdown links.
    fence = "`" * (max((len(part) for part in re.findall(r"`+", text)), default=2) + 1)
    return f"{fence}text\n{text}\n{fence}"


def render(analysis: Analysis) -> str:
    lines = [
        f"# {analysis.company} — kaynaklı inceleme",
        "",
        f"Bilgi kesimi: **{analysis.as_of} gün sonu (America/New_York)**. "
        f"Çalışma: `{analysis.run_id}`. Durum: **{analysis.status}**.",
        "",
        f"Sonuç etiketi: **{analysis.overall}**.",
        "",
        "Bu etiket tanımlı kurallara ve aşağıdaki kaynaklara aittir; yatırım güvenliği yüzdesi veya çöküş olasılığı değildir.",
        "",
        "## Hesaplanan göstergeler",
        "",
        "| Dönem | Gösterge | Değer | Birim |",
        "|---|---|---:|---|",
    ]
    for metric in analysis.metrics:
        lines.append(f"| {metric.period} | {metric.name} | {metric.value:.4f} | {metric.unit} |")
    if not analysis.metrics:
        lines.extend(["", "Hesaplanabilir, kontrol edilmiş gösterge yok."])
    block_lookup = {block.id: block for block in analysis.blocks}
    fact_lookup = {fact.id: fact for fact in analysis.facts}
    lines.extend(["", "## Bulgular", ""])
    for finding in analysis.findings:
        lines.extend(
            [
                f"### {finding.title}",
                "",
                f"**{STATUS[finding.status]}** — {finding.explanation}",
                "",
            ]
        )
        references = list(finding.evidence)
        references.extend(
            fact_lookup[fid].evidence for fid in finding.fact_ids if fid in fact_lookup
        )
        seen = set()
        for ref in references:
            key = (ref.block_id, ref.quote)
            if key in seen:
                continue
            seen.add(key)
            block = block_lookup.get(ref.block_id)
            where = f"sayfa {block.page}, " if block and block.page else ""
            lines.extend(
                [f"Kaynak konumu: {where}blok `{ref.block_id}`.", "", literal(ref.quote), ""]
            )
    if not analysis.findings:
        lines.extend(["Yeterli bulgu üretilemedi; bu, risk olmadığı anlamına gelmez.", ""])
    lines.extend(["## Kaynaklar", ""])
    for source in analysis.sources:
        lines.extend(
            [
                f"- {source.url}",
                f"  - Yayın: {source.publication_date}; edinim: {source.retrieved_at.isoformat()}; önbellek: {source.cached}.",
                f"  - SHA-256: `{source.sha256}`.",
                f"  - {source.version_note}",
                f"  - Yayın kanıtı: {source.publication_proof}",
            ]
        )
    lines.extend(["", "## Eksikler ve sınırlar", ""])
    lines.extend(f"- {item}" for item in analysis.limitations)
    if analysis.rejected:
        lines.append(
            f"- {len(analysis.rejected)} çıkarım/satır reddedildi; ayrıntılar JSON çıktısında."
        )
    lines.extend(["", "## Çalışma süreleri", ""])
    lines.extend(f"- {stage}: {seconds:.3f} saniye" for stage, seconds in analysis.timings.items())
    return "\n".join(lines) + "\n"
