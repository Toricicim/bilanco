from decimal import Decimal

from .models import Fact, Finding, Metric

BASE_CONCEPTS = {
    "current_assets",
    "current_liabilities",
    "total_assets",
    "equity",
    "cash",
    "long_term_debt",
    "net_income",
    "operating_cash_flow",
}


def calculate(facts: list[Fact]) -> tuple[list[Metric], list[Finding], list[str]]:
    lookup = {(f.concept, f.period): f for f in facts}
    periods = sorted({f.period for f in facts}, reverse=True)[:2]
    metrics: list[Metric] = []
    findings: list[Finding] = []
    missing: list[str] = []

    def ratio(name: str, label: str, numerator: str, denominator: str, year: int) -> Metric | None:
        a, b = lookup.get((numerator, year)), lookup.get((denominator, year))
        if not a or not b or a.unit == "unknown" or a.unit != b.unit or b.value <= 0:
            missing.append(f"{year}: {label} için kullanılabilir/payda-pozitif veri yok.")
            return None
        metric = Metric(
            id=f"{name}_{year}",
            period=year,
            name=label,
            value=(a.value * a.scale) / (b.value * b.scale),
            unit="ratio",
            formula=f"{numerator} / {denominator}",
            fact_ids=[a.id, b.id],
        )
        metrics.append(metric)
        return metric

    def add(metric: Metric, status: str, title: str, detail: str) -> None:
        findings.append(
            Finding(
                id=metric.id,
                category="financial",
                status=status,
                title=title,
                explanation=detail,
                fact_ids=metric.fact_ids,
            )
        )

    for year in periods:
        current = ratio("current_ratio", "Cari oran", "current_assets", "current_liabilities", year)
        if current:
            add(
                current,
                "signal" if current.value < 1 else "context",
                f"{year}: kısa vadeli yükümlülükler",
                f"Cari oran {current.value:.3f}. "
                + (
                    "Dönen varlıkların defter değeri kısa vadeli yükümlülüklerin altında."
                    if current.value < 1
                    else "Dönen varlıkların defter değeri kısa vadeli yükümlülükleri karşılıyor; bu tek başına nakit yeterliliği ölçümü değildir."
                ),
            )
        cash = ratio(
            "cash_ratio", "Nakit / kısa vadeli yükümlülük", "cash", "current_liabilities", year
        )
        if cash:
            add(
                cash,
                "context",
                f"{year}: nakit tamponu",
                f"Nakit ve nakit benzerleri / kısa vadeli yükümlülük {cash.value:.3f}. Sektör karşılaştırması yapılmadı.",
            )
        debt = ratio(
            "long_debt_equity", "Uzun vadeli borç / özkaynak", "long_term_debt", "equity", year
        )
        if debt:
            add(
                debt,
                "context",
                f"{year}: uzun vadeli borç",
                f"Uzun vadeli borç / özkaynak {debt.value:.3f}; toplam borç veya garanti toplamı değildir.",
            )
        cash_profit = ratio(
            "cash_profit", "Faaliyet nakdi / net kâr", "operating_cash_flow", "net_income", year
        )
        if cash_profit:
            add(
                cash_profit,
                "signal" if cash_profit.value <= 0 else "context",
                f"{year}: kâr ve faaliyet nakdi",
                f"Faaliyet nakdi / net kâr {cash_profit.value:.3f}. "
                + (
                    "Pozitif net kâra rağmen faaliyet nakdi pozitif değil."
                    if cash_profit.value <= 0
                    else "Faaliyet nakdi pozitif. Nakit akışı kalemlerinin niteliği ayrıca incelenmeli."
                ),
            )
        assets, liabilities, equity = (
            lookup.get((c, year)) for c in ("total_assets", "total_liabilities", "equity")
        )
        if (
            assets
            and liabilities
            and equity
            and len({f.unit for f in (assets, liabilities, equity)}) == 1
        ):
            difference = (
                assets.value * assets.scale
                - liabilities.value * liabilities.scale
                - equity.value * equity.scale
            )
            # Published statements may be rounded to the displayed scale.
            tolerance = Decimal(max(f.scale for f in (assets, liabilities, equity)))
            if abs(difference) > tolerance:
                findings.append(
                    Finding(
                        id=f"balance_mismatch_{year}",
                        category="data_quality",
                        status="needs_review",
                        title=f"{year}: bilanço eşitliği uyuşmuyor",
                        explanation="Kopyalanan değerler değiştirilmedi. Tablo çıkarımı veya kaynak kontrol edilmeli.",
                        fact_ids=[assets.id, liabilities.id, equity.id],
                    )
                )
                missing.append(f"{year}: bilanço eşitliği kontrolü başarısız.")
    if len(periods) == 2:
        new, old = periods
        growth = {}
        for concept, label in (
            ("net_income", "Net kâr"),
            ("operating_cash_flow", "Faaliyet nakdi"),
        ):
            a, b = lookup.get((concept, new)), lookup.get((concept, old))
            if a and b and a.unit != "unknown" and a.unit == b.unit and b.value > 0:
                value = ((a.value * a.scale) / (b.value * b.scale) - 1) * 100
                growth[concept] = value
                metrics.append(
                    Metric(
                        id=f"{concept}_growth_{new}",
                        period=new,
                        name=f"{label} değişimi",
                        value=value,
                        unit="percent",
                        formula=f"({concept}[{new}] / {concept}[{old}] - 1) * 100",
                        fact_ids=[a.id, b.id],
                    )
                )
        if {"net_income", "operating_cash_flow"} <= growth.keys():
            if growth["net_income"] > 0 > growth["operating_cash_flow"]:
                refs = [lookup[(concept, year)].id for concept in growth for year in periods]
                findings.append(
                    Finding(
                        id=f"cash_profit_divergence_{new}",
                        category="financial",
                        status="signal",
                        title="Kâr artarken faaliyet nakdi düşüyor",
                        explanation=f"Net kâr değişimi %{growth['net_income']:.2f}, faaliyet nakdi değişimi %{growth['operating_cash_flow']:.2f}. Bu bir inceleme işaretidir; faaliyet nakdinin negatif olduğunu veya hileyi göstermez.",
                        fact_ids=refs,
                    )
                )
    for year in periods:
        for concept in sorted(BASE_CONCEPTS):
            if (concept, year) not in lookup:
                missing.append(f"Eksik alan: {concept}, {year}.")
    if len(periods) < 2:
        missing.append("İki karşılaştırılabilir finansal dönem bulunamadı.")
    return metrics, findings, missing


def overall(findings: list[Finding], missing: list[str]) -> str:
    if any(f.status == "signal" for f in findings):
        return "inceleme_isareti_var"
    if missing:
        return "yetersiz_veri"
    if any(f.status == "needs_review" for f in findings):
        return "inceleme_gerekli"
    return "tanimli_kurallarda_isaret_yok"
