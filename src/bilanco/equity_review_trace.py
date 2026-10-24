"""Observable check coverage and a review queue, separate from a calibrated risk verdict."""

from .equity_models import CheckTrace, InvestorReview


def review_trace(analysis, findings, checks):
    source_coverage = analysis.ai.get("source_coverage", {})
    scanned = sum(
        bool(e.get("planned") and e.get("planned") == e.get("processed") and not e.get("failed"))
        for e in source_coverage.values()
    )
    traces = []

    def add(ident, title, status, candidates, rejected, mids, fids, missing):
        traces.append(
            CheckTrace(
                id=ident,
                title=title,
                status=status,
                sources_acquired=len(analysis.sources),
                sources_scanned=scanned,
                candidates_accepted=candidates,
                candidates_rejected=len(rejected),
                rejection_reasons=sorted({r.get("reason", "unknown") for r in rejected}),
                metric_ids=list(dict.fromkeys(mids)),
                finding_ids=list(dict.fromkeys(fids)),
                missing_inputs=missing,
            )
        )

    for check in checks:
        add(
            check.id,
            check.title,
            check.status,
            sum(o.kind == check.id for o in analysis.signals),
            [r for r in analysis.rejected if r.get("kind") == check.id],
            check.metric_ids,
            check.finding_ids,
            check.missing_inputs,
        )
    comparisons = analysis.comparisons
    add(
        "document_comparison",
        "Nötr olgulardan belge karşılaştırması",
        "evidence_found"
        if any(c.status in {"difference", "consistent"} for c in comparisons)
        else "partial"
        if analysis.document_facts
        else "unavailable",
        len(analysis.document_facts),
        [r for r in analysis.rejected if r.get("reason", "").startswith("document_fact_")],
        [m for c in comparisons for m in c.metric_ids],
        [f.id for f in findings if f.rule_id.startswith("D-")],
        list(dict.fromkeys([x for c in comparisons for x in c.missing_inputs]))
        or (
            []
            if comparisons
            else ["Aynı konu/dönem/baz için karşılaştırılabilir en az iki kaynak olgusu."]
        ),
    )
    add(
        "fund_liquidity",
        "Şirket → fon maruziyeti ve likidite izi",
        "partial" if analysis.fund_exposures else "unavailable",
        sum(f.kind.startswith("fund_") for f in analysis.document_facts),
        [
            r
            for r in analysis.rejected
            if r.get("stage") == "related_fund" or r.get("kind", "").startswith("fund_")
        ],
        [m for e in analysis.fund_exposures for m in e.metric_ids],
        [],
        list(dict.fromkeys(x for e in analysis.fund_exposures for x in e.missing_inputs))
        or ["Tarihli şirket fon pozisyonu, fon belgesi ve uygulanabilir iade/borç şartları."],
    )
    add(
        "financial_history",
        "Birden çok dönemde kâr/nakit geçmişi",
        "partial" if analysis.financial_history else "unavailable",
        len(analysis.financial_history),
        [],
        [],
        [],
        ["Karşılaştırılabilir sektör/mevsimsellik emsali; yeterli tarihsel dönem kapsamı."],
    )
    return traces


def investor_review(findings, traces):
    ids = list(
        dict.fromkeys(
            f.id for f in findings if f.level in {"review", "critical"} and f.origin == "indicator"
        )
    )
    incomplete = [t.id for t in traces if t.status != "evidence_found" or t.missing_inputs]
    status = (
        "inceleme_gerekli" if ids else "veri_yetersiz" if incomplete else "belirgin_ek_isaret_yok"
    )
    message = {
        "inceleme_gerekli": "Bu hisseyi değerlendirmeden önce aşağıdaki bulguları ve karşı açıklamaları inceleyin. Bu bir dolandırıcılık veya çöküş tahmini değildir.",
        "veri_yetersiz": "İnceleme için yeterli doğrulanmış veri yok; bu sonuç hissenin güvenli olduğunu göstermez.",
        "belirgin_ek_isaret_yok": "Değerlendirilebilen kontrollerde ek inceleme işareti oluşmadı; yatırım güvenliği sonucu değildir.",
    }[status]
    return InvestorReview(
        status=status,
        message=message,
        finding_ids=ids,
        incomplete_checks=incomplete,
        limitations=[
            "Bu çıktı inceleme kuyruğudur; kalibre edilmiş risk olasılığı değildir.",
            "Kalibrasyonsuz adaylar burada görünür; mevcut genel şirket sonucuna otomatik ek oy verilmez.",
            "Kaynak havuzunun taranması, her kontrol için bütün ekonomik verinin mevcut olduğunu kanıtlamaz.",
        ],
    )
