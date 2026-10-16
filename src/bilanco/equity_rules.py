"""Frozen, uncalibrated review rules. Outcomes are not fraud probabilities."""

from datetime import timedelta
from decimal import Decimal
from statistics import mean

from .equity_models import EquityAnalysis, Metric, ReviewFinding
from .equity_sources import fold

DOMAINS = ("financial", "operations", "relations", "audit", "market")


def evaluate(analysis: EquityAnalysis):
    metrics: list[Metric] = []
    findings: list[ReviewFinding] = []
    coverage = dict.fromkeys(DOMAINS, "unavailable")
    block_sources = {b.id: b.source_id for b in analysis.blocks}
    source_map = {s.id: s for s in analysis.sources}
    financial = sorted(
        (s for s in analysis.sources if s.kind == "financial"), key=lambda s: s.available_at
    )
    source = financial[-1] if financial else None
    audited = [
        s
        for s in financial
        if "denetim sonucu"
        in fold(" ".join(b.text for b in analysis.blocks if b.source_id == s.id)[:7000])
    ]
    latest_audit = audited[-1] if audited else source
    facts = [f for f in analysis.facts if source and f.source_id == source.id]
    end = max((f.period_end for f in facts), default=None)
    flows = [f for f in facts if f.period_start is not None and f.period_end == end]
    if flows:
        start = min(f.period_start for f in flows)
    else:
        start = None
    current = {
        f.concept: f for f in facts if f.period_end == end and f.period_start in (None, start)
    }
    previous_end = None
    if end:
        try:
            previous_end = end.replace(year=end.year - 1)
        except ValueError:
            previous_end = end.replace(year=end.year - 1, day=28)
    previous = {
        f.concept: f
        for f in facts
        if f.period_end == previous_end
        and (
            f.period_start is None
            or start
            and (f.period_start.month, f.period_start.day) == (start.month, start.day)
        )
    }
    consistent_basis = len({(f.basis_date, f.scope, f.currency) for f in facts}) <= 1

    def metric(name, domain, value, formula, inputs=(), unit="ratio", source_ids=()):
        obj = Metric(
            id=name,
            domain=domain,
            value=value,
            unit=unit,
            formula=formula,
            fact_ids=[f.id for f in inputs],
            source_ids=list(source_ids),
        )
        metrics.append(obj)
        return obj

    def flag(
        rule,
        domain,
        title,
        explanation,
        used=(),
        level="review",
        evidence=(),
        counter=(),
        unknowns=(),
        origin="indicator",
    ):
        # One rule occurrence per snapshot, not repeated independent votes.
        findings.append(
            ReviewFinding(
                id=rule,
                domain=domain,
                rule_id=rule,
                level=level,
                title=title,
                explanation=explanation,
                metric_ids=list(used),
                evidence=list(evidence),
                counter_evidence=list(counter),
                unknowns=list(unknowns),
                origin=origin,
            )
        )

    if current:
        coverage["financial"] = "partial"
    if {
        "net_income",
        "operating_cash_flow",
        "cash",
        "current_assets",
        "current_liabilities",
        "equity",
        "short_debt",
        "current_long_debt",
    } <= current.keys():
        coverage["financial"] = "available"
    if {"net_income", "operating_cash_flow"} <= current.keys():
        net, cash = current["net_income"], current["operating_cash_flow"]
        metric(
            "profit_cash_gap",
            "financial",
            net.value - cash.value,
            "net_income - operating_cash_flow",
            [net, cash],
            "TRY",
        )
        if net.value > 0:
            metric(
                "cash_profit",
                "financial",
                cash.value / net.value,
                "operating_cash_flow / net_income",
                [net, cash],
            )
        if net.value > 0 and cash.value < 0:
            flag(
                "F01",
                "financial",
                "Kâr açıklanırken faaliyet nakdi negatif",
                "Tahsilat, işletme sermayesi, avanslar ve nakit dışı düzeltmelerle birlikte incelenmeli.",
                ["profit_cash_gap"],
                evidence=[net.evidence, cash.evidence],
            )
    if "equity" in current and current["equity"].value < 0:
        flag(
            "F02",
            "financial",
            "Negatif özkaynak",
            "Yükümlülükler varlıkları aşmış; sermaye ve ödeme gücü incelemesi gerekir.",
            level="critical",
            evidence=[current["equity"].evidence],
        )
    if {"current_assets", "current_liabilities"} <= current.keys() and current[
        "current_liabilities"
    ].value > 0:
        a, b = current["current_assets"], current["current_liabilities"]
        metric(
            "current_ratio",
            "financial",
            a.value / b.value,
            "current_assets / current_liabilities",
            [a, b],
        )
    debt_names = {"cash", "short_debt", "current_long_debt"}
    if debt_names <= current.keys():
        debt = current["short_debt"].value + current["current_long_debt"].value
        if debt > 0:
            value = current["cash"].value / debt
            metric(
                "cash_short_financial_debt",
                "financial",
                value,
                "cash / (short_debt + current_long_debt)",
                [current[k] for k in sorted(debt_names)],
            )
            if (
                value < Decimal("0.25")
                and current.get("operating_cash_flow")
                and current["operating_cash_flow"].value < 0
            ):
                flag(
                    "F03",
                    "financial",
                    "Yaklaşan finansal borca göre nakit sınırlı",
                    "Nakit oranı 0,25'in altında ve faaliyet nakdi negatif. Finansal yatırımların likiditesi, blokajlar ve borç vadeleri ayrıca incelenmeli.",
                    ["cash_short_financial_debt"],
                    evidence=[current[k].evidence for k in sorted(debt_names)],
                    unknowns=[
                        "Serbest nakit/blokaj ve finansal yatırım likiditesi bu orandan çıkarılamaz."
                    ],
                )
    if {"total_assets", "total_liabilities", "equity"} <= current.keys():
        a, liabilities, e = (current[k] for k in ("total_assets", "total_liabilities", "equity"))
        error = a.value - liabilities.value - e.value
        metric(
            "balance_error",
            "financial",
            error,
            "assets - liabilities - equity",
            [a, liabilities, e],
            "TRY",
        )
        if abs(error) > max(Decimal(1), abs(a.value) * Decimal("0.000001")):
            coverage["financial"] = "invalid"
            flag(
                "DQ01",
                "financial",
                "Tablo eşitliği doğrulanamadı",
                "Hesap/çıkarım kalitesi sorunu; şirket riski olarak sayılmadı.",
                ["balance_error"],
                level="context",
                evidence=[a.evidence, liabilities.evidence, e.evidence],
            )
            # No numerical alarm may survive invalid source table arithmetic.
            findings = [
                f.model_copy(
                    update={
                        "level": "context",
                        "unknowns": f.unknowns + ["Finansal tablo eşitliği doğrulanamadı."],
                    }
                )
                if f.domain == "financial"
                else f
                for f in findings
            ]
    if {"monetary_gain", "pretax_profit"} <= current.keys() and current["pretax_profit"].value > 0:
        a, b = current["monetary_gain"], current["pretax_profit"]
        metric(
            "monetary_gain_pretax",
            "financial",
            a.value / b.value,
            "monetary_gain / pretax_profit",
            [a, b],
        )
        flag(
            "F04",
            "financial",
            "Parasal pozisyon etkisi ayrı gösterildi",
            "TMS 29 parasal kazancı nakit girişi değildir; tek başına alarm sayılmadı.",
            ["monetary_gain_pretax"],
            level="context",
            evidence=[a.evidence, b.evidence],
        )
    if {"financing_expense", "revenue"} <= current.keys() and current["revenue"].value > 0:
        a, b = current["financing_expense"], current["revenue"]
        metric(
            "financing_revenue",
            "financial",
            abs(a.value) / b.value,
            "abs(financing_expense) / revenue",
            [a, b],
        )
    if all("revenue" in view and view["revenue"].value > 0 for view in (current, previous)):
        r, old = current["revenue"], previous["revenue"]
        growth = r.value / old.value - 1
        metric("revenue_growth", "operations", growth, "revenue / comparable_revenue - 1", [r, old])
        coverage["operations"] = "partial"
        if all("operating_profit" in view for view in (current, previous)):
            op, prev_op = current["operating_profit"], previous["operating_profit"]
            margin, prev_margin = op.value / r.value, prev_op.value / old.value
            metric("operating_margin", "operations", margin, "operating_profit / revenue", [op, r])
            metric(
                "margin_change",
                "operations",
                margin - prev_margin,
                "operating_margin - comparable_margin",
                [op, r, prev_op, old],
                "percentage_points_fraction",
            )
            coverage["operations"] = "available"
            if growth <= Decimal("-0.20") and margin - prev_margin <= Decimal("-0.05"):
                flag(
                    "O01",
                    "operations",
                    "Satış ve faaliyet marjında birlikte gerileme",
                    "Aynı satın alma gücüyle satış en az %20, faaliyet marjı en az 5 puan gerilemiş.",
                    ["revenue_growth", "margin_change"],
                    evidence=[r.evidence, old.evidence, op.evidence, prev_op.evidence],
                )
        if (
            "receivables" in current
            and "receivables" in previous
            and previous["receivables"].value > 0
            and start
        ):
            ar, ar_old = current["receivables"], previous["receivables"]
            days = Decimal((r.period_end - r.period_start).days + 1)
            old_days = Decimal((old.period_end - old.period_start).days + 1)
            proxy, prev_proxy = ar.value * days / r.value, ar_old.value * old_days / old.value
            gap = ar.value / ar_old.value - 1 - growth
            metric(
                "receivable_days_proxy",
                "financial",
                proxy,
                "period_end_receivables * period_days / revenue",
                [ar, r],
                "days",
            )
            metric(
                "receivable_days_change",
                "financial",
                proxy - prev_proxy,
                "receivable_days_proxy - comparable_proxy",
                [ar, r, ar_old, old],
                "days",
            )
            metric(
                "receivable_growth_gap",
                "financial",
                gap,
                "receivables_growth - revenue_growth",
                [ar, ar_old, r, old],
            )
            if proxy - prev_proxy >= 30 and gap >= Decimal("0.20"):
                flag(
                    "F05",
                    "financial",
                    "Satışa göre alacak birikimi",
                    "Dönem sonu alacaklarla tahsil süresi vekili en az 30 gün, büyüme farkı en az 20 puan artmış. Bu, gerçek fatura vade/gecikme ölçümü değildir.",
                    ["receivable_days_change", "receivable_growth_gap"],
                    evidence=[ar.evidence, r.evidence, ar_old.evidence, old.evidence],
                )
    if "revenue" in current:
        actual = current["revenue"]

        def forecast_time(forecast):
            return max(
                source_map[block_sources[r.block_id]].available_at for r in forecast.evidence
            )

        for forecast in sorted(analysis.forecasts, key=forecast_time, reverse=True):
            if (
                forecast.period_start,
                forecast.period_end,
                forecast.basis_date,
                forecast.currency,
            ) != (actual.period_start, actual.period_end, actual.basis_date, actual.currency):
                continue
            from .equity_tables import parse_turkish

            amount = parse_turkish(forecast.amount_text)
            if amount <= 0:
                continue
            ratio = actual.value / amount
            metric(
                "forecast_achievement",
                "operations",
                ratio,
                "actual_revenue / stated_forecast",
                [actual],
            )
            if ratio < Decimal("0.80"):
                flag(
                    "O02",
                    "operations",
                    "Satış tahmininin %80'inden azı gerçekleşmiş",
                    "Dönemi, para birimi ve satın alma gücü eşleştirilmiş karşılaştırma.",
                    ["forecast_achievement"],
                    evidence=[actual.evidence, *forecast.evidence],
                )
            break

    claims_by_kind = {}
    for claim in analysis.claims:
        claims_by_kind.setdefault(claim.kind, []).append(claim)
        if claim.kind == "relation" and claim.relation:
            from .assessment import classify

            priority, rule, explanation = classify(claim.relation)
            flag(
                f"R-{len(findings)}",
                "relations",
                "İlişkili işlem / yönetici bağlantısı",
                explanation,
                level="review" if priority == "first_review" else "context",
                evidence=claim.evidence,
                counter=claim.counter_evidence,
                unknowns=[
                    k
                    for k in ("financial_effect", "business_purpose", "controls")
                    if getattr(claim.relation, k).answer in {"unknown", "conflicting"}
                ],
            )
        elif claim.kind in {"adverse_opinion", "disclaimer", "going_concern", "qualified_opinion"}:
            claim_sources = {
                source_map[block_sources[r.block_id]].disclosure_id for r in claim.evidence
            }
            current_audit = latest_audit is not None and claim_sources == {
                latest_audit.disclosure_id
            }
            flag(
                f"A-{len(findings)}",
                "audit",
                {
                    "adverse_opinion": "Olumsuz denetçi görüşü",
                    "disclaimer": "Denetçi görüş vermekten kaçınmış",
                    "going_concern": "İşletmenin sürekliliğinde önemli belirsizlik",
                    "qualified_opinion": "Sınırlı olumlu denetçi görüşü",
                }[claim.kind],
                "Şirkete özgü alıntı; genel denetim sorumluluğu metniyle karıştırılmamalı.",
                level=("review" if claim.kind == "qualified_opinion" else "critical")
                if current_audit
                else "context",
                evidence=claim.evidence,
                counter=claim.counter_evidence,
                unknowns=[]
                if current_audit
                else ["Önceki raporun denetim açıklaması; son raporun görüşü olarak sayılmadı."],
            )
        elif claim.kind == "regulatory":
            flag(
                f"REG-{len(findings)}",
                "market",
                "O tarihte bilinen düzenleyici açıklama",
                "Tarihsel tedbir açıklaması; yeni göstergeden tahmin veya tedbirin hâlen yürürlükte olduğu sonucu değildir.",
                level="context",
                evidence=claim.evidence,
                origin="known_regulatory",
            )
        elif claim.kind == "disclosure_issue":
            flag(
                f"D-{len(findings)}",
                "audit",
                "Açıklanmış raporlama sorunu",
                "Alıntılı düzeltme/gecikme bağlamı; otomatik hile sonucu değildir.",
                level="context",
                evidence=claim.evidence,
                counter=claim.counter_evidence,
            )
        elif claim.kind in {"operation", "counterstatement"}:
            flag(
                f"C-{len(findings)}",
                "operations" if claim.kind == "operation" else "relations",
                "Faaliyet açıklaması"
                if claim.kind == "operation"
                else "Dengeleyici şirket açıklaması",
                "Kaynakta yer alan beyan; bağımsız doğrulama sayılmaz.",
                level="context",
                evidence=claim.evidence,
            )
    if analysis.ai.get("extraction_complete"):
        if any(
            s.kind in {"financial", "financial_attachment", "activity", "attachment", "disclosure"}
            for s in analysis.sources
        ):
            coverage["relations"] = "text_scanned"
        if financial:
            coverage["audit"] = "text_scanned"
    # Holdings remain observations, never inferred beneficial ownership or an additive sum.
    for holding in analysis.holdings:
        flag(
            f"H-{len(findings)}",
            "market",
            f"Açıklanmış pay: {holding.holder}",
            f"{holding.effective_date}: {holding.percentage_text}; baz: {holding.basis}. Nihai kişi veya ortak hareket sonucu çıkarılmadı.",
            level="context",
            evidence=holding.evidence,
        )

    series = {s.symbol: s for s in analysis.market}
    stock = next((s for symbol, s in series.items() if symbol != "XU100.IS"), None)
    benchmark = series.get("XU100.IS")
    if stock and benchmark:
        x = {b.day: b for b in stock.bars if b.day <= analysis.as_of}
        y = {b.day: b for b in benchmark.bars if b.day <= analysis.as_of}
        days = sorted(x.keys() & y.keys())
        fresh = bool(days and analysis.as_of - days[-1] <= timedelta(days=7))
        if len(days) >= 61 and fresh:
            coverage["market"] = "price_available_depth_unavailable"
            for window in (20, 60):
                ret = x[days[-1]].close / x[days[-window - 1]].close - 1
                idx = y[days[-1]].close / y[days[-window - 1]].close - 1
                metric(
                    f"return_{window}",
                    "market",
                    ret,
                    f"close_t / close_t_minus_{window} - 1",
                    source_ids=[stock.sha256],
                )
                metric(
                    f"excess_{window}",
                    "market",
                    ret - idx,
                    f"stock_return_{window} - XU100_return_{window}",
                    source_ids=[stock.sha256, benchmark.sha256],
                )
                if window == 60 and ret >= 1 and ret - idx >= Decimal("0.50"):
                    flag(
                        "M01",
                        "market",
                        "Piyasadan belirgin fiyat ayrışması",
                        "60 işlem gününde en az %100 yükseliş ve endeksten en az 50 puan ayrışma. Manipülasyon kanıtı değildir.",
                        ["return_60", "excess_60"],
                    )
            vols = [x[d].volume for d in days[-80:]]
            if len(vols) == 80 and all(v is not None for v in vols) and mean(vols[:60]) > 0:
                metric(
                    "relative_volume",
                    "market",
                    mean(vols[-20:]) / mean(vols[:60]),
                    "mean(volume_last_20) / mean(volume_previous_60)",
                    source_ids=[stock.sha256],
                )
    seen = set()
    deduped = []
    for f in findings:
        key = (
            f.domain,
            f.rule_id
            if not f.evidence
            else (f.title, tuple((r.block_id, r.quote) for r in f.evidence)),
        )
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    indicators = [f for f in deduped if f.origin == "indicator" and f.level != "context"]
    domains = {f.domain for f in indicators}
    if any(f.level == "critical" for f in indicators) or len(domains) >= 2:
        outcome = "dikkat_gerektiriyor"
    elif indicators:
        outcome = "sinirli_isaret"
    elif coverage["financial"] != "available" or not coverage["market"].startswith(
        "price_available"
    ):
        outcome = "yetersiz_veri"
    else:
        outcome = "belirgin_isaret_yok"
    # Invalid tables must not indirectly drive operational alarms either.
    if coverage["financial"] == "invalid" or not consistent_basis:
        coverage["financial"] = "invalid"
        coverage["operations"] = "invalid"
        deduped = [
            f.model_copy(update={"level": "context"})
            if f.domain in {"financial", "operations"}
            else f
            for f in deduped
        ]
        domains = {f.domain for f in deduped if f.level != "context" and f.origin == "indicator"}
        outcome = (
            "dikkat_gerektiriyor"
            if any(f.level == "critical" for f in deduped) or len(domains) >= 2
            else "sinirli_isaret"
            if domains
            else "yetersiz_veri"
        )
    return metrics, deduped, coverage, outcome
