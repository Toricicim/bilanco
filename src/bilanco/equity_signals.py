"""Shared investor review catalogue. Evidence, measurements and unknowns stay separate."""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .documents import normalize
from .equity_models import Metric, ReviewFinding, SignalCheck
from .equity_sources import fold
from .storage import digest


@dataclass(frozen=True)
class SignalSpec:
    title: str
    domain: str
    terms: str
    issue: str
    missing: str
    metrics: tuple[str, ...] = ()
    rules: tuple[str, ...] = ()


CATALOG = {
    "cash_collection": SignalSpec(
        "Kâr, nakit ve tahsilatın uyumu",
        "financial",
        r"nakit|tahsil|alacak",
        r"tahsil edile|vadesi gec|nakit acigi|nakit akis.{0,35}negatif",
        "Aylık tahsilatlar, yaşlandırma, birden çok dönemin nakit köprüsü",
        (
            "cash_profit",
            "receivable_days_proxy",
            "receivable_average_days",
            "cash_conversion_mismatch_periods",
            "cashflow_investment_adjustment_share",
        ),
        ("F01", "F05"),
    ),
    "related_receivables": SignalSpec(
        "Ortak ve ilişkili taraflarda kalan kaynak",
        "relations",
        r"iliskili|ortak",
        r"tahsil edile|vadesi gec|vadesi uzatil|vadesi ertelen|karsilik ayril",
        "Vade, faiz, brüt bakiye, tahsilat ve karşı teminat",
        ("current_related_receivables_assets", "noncurrent_related_receivables_assets"),
    ),
    "related_terms": SignalSpec(
        "İlişkili varlık, kira ve teminat koşulları",
        "relations",
        r"iliskili|ana ortak|kirala|teminat|degerleme",
        r"onaysiz|onay alinma|degerleme yapilma|piyasa kosullarina aykiri|sirket aleyhine|zarara ugrat|bedelsiz",
        "Aynı varlık/taraf için bedel, kira, değerleme, onay ve ekonomik fayda",
        rules=("R02",),
    ),
    "liquidity": SignalSpec(
        "Yakın borç ve kullanılabilir kaynak",
        "financial",
        r"borc|kredi|likidite|nakit|mevduat",
        r"vadesinde odenme|temerru|sozlesme ihlal|nakit acigi|likidite acigi|bloke|kisitli",
        "Sözleşmesel vade, blokaj, fon valörü ve taahhütlü kredi",
        ("cash_short_financial_debt", "current_ratio"),
        ("F03",),
    ),
    "earnings_quality": SignalSpec(
        "Faaliyet sonucu ve kâr bileşenleri",
        "financial",
        r"kar|gelir|kazanc|degerleme|karsilik",
        r"tek seferlik|bir defalik|karsilik iptal|gercege uygun deger|varlik satis",
        "Tek seferlik gelirlerin, tahminlerin ve parasal etkinin dipnot ayrımı",
        ("operating_profit_pretax", "investment_income_pretax", "monetary_gain_pretax"),
    ),
    "execution": SignalSpec(
        "Açıklanan işin ve tahminin gerçekleşmesi",
        "operations",
        r"sozlesme|proje|siparis|hedef|tahmin|teslim",
        r"iptal edil|feshedil|tamamlanama|gerceklesme.{0,20}(?:dusuk|altinda)|hedef.{0,25}ulasilama|teslim.{0,25}gecik",
        "Aynı olayın sözleşme/niyet ayrımı, takvimi ve aynı bazda gerçekleşmesi",
        ("forecast_achievement",),
        ("O02",),
    ),
    "proceeds_use": SignalSpec(
        "Halka arz ve bedelli gelirinin kullanımı",
        "operations",
        r"halka arz|sermaye artir|fon kullanim",
        r"amac.{0,20}disinda|plana aykiri|taahhud.{0,25}aykiri|kullanim.{0,20}sapma",
        "İlk plan, takvim, değişiklik izni, gerçekleşen kullanım ve kalan kaynak",
    ),
    "audit_specific": SignalSpec(
        "Belirli kalemde denetim yanlışlığı veya kanıt kısıtı",
        "audit",
        r"denet|gorus|kanit|teyit",
        r"yeterli.{0,40}kanit.{0,20}(?:elde edile|saglanama)|teyit edile|sinirli olumlu|sartli gorus|olumsuz gorus|gorus vermekten kacin|sureklilig.{0,80}onemli belirsizlik",
        "Güncel görüşün dayanağı, etkilenen kalem/tutar ve önceki dönemden farkı",
    ),
    "report_consistency": SignalSpec(
        "Aynı olay veya tablolar arasında tutarlılık",
        "audit",
        r"rapor|tablo|aciklama|sozlesme|unvan",
        r"celiski|sehven|hatali|yeniden duzenle|yanlis|gercegi yansitma|duzelt",
        "İlk sürüm, düzeltme, aynı dönem/taraf/kapsam ve tutar etkisi",
    ),
    "insider_sales": SignalSpec(
        "Olumlu anlatımla birlikte ortak/yönetici net satışı",
        "market",
        r"ortak|yonetici|pay sahibi",
        r"net satis|pay satis|hisse satis",
        "Tarihli net alım/satım, halka arz/virman ayrımı ve aynı dönem anlatımı",
    ),
    "price_operations": SignalSpec(
        "Fiyat-hacim ve faaliyet/emsal ayrışması",
        "market",
        r"fiyat|hacim|getiri",
        r"ayris|olagan disi|olagandisi",
        "Sektör ve likidite emsalleri, sermaye işlemleri ve faaliyet haberleri",
        ("return_60", "excess_60", "relative_volume"),
        ("M01",),
    ),
    "exit_concentration": SignalSpec(
        "Çıkış likiditesi ve açıklanmış pay yoğunlaşması",
        "market",
        r"saklama|fon|pay|derinlik|alis satis",
        r"yogunlas|likidite|spread|derinlik|fiyat etkisi",
        "Tarihli fon/saklama payları, dolaşım, spread ve pozisyon bazlı fiyat etkisi",
    ),
    "closing_pattern": SignalSpec(
        "Tekrarlayan kapanış sıçraması ve çözülme",
        "market",
        r"kapanis|muzayede",
        r"sictama|sicrama|yukselt|yukselis|geri donus|cozulme",
        "Gün içi ve müzayede işlemleri; sonraki açılış ancak kesimden önceyse",
    ),
    "order_cancellations": SignalSpec(
        "Tekrarlayan büyük emir iptalleri",
        "market",
        r"emir|kotasyon",
        r"iptal|geri cek",
        "Emir ekleme/değiştirme/iptal geçmişi, büyüklük, ömür ve gerçekleşme",
    ),
    "inventory_contracts": SignalSpec(
        "Stok ve sözleşme varlıklarının dönüşümü",
        "financial",
        r"stok|sozlesme varli[kg]|hakedi",
        r"stoklar.{0,30}yaslan|deger dusuk.{0,30}yetersiz|karsilik.{0,30}yetersiz|donus.{0,20}uza|tahsil edile",
        "Stok/sözleşme yaşlandırması, proje takvimi ve karşılık hesabı",
        ("inventory_days", "inventory_growth_gap", "current_contract_assets_revenue"),
    ),
}


def signal_error(obj, mapping, source, company, *, issuer_valid, references_valid, dates_in):
    refs = obj.evidence + obj.counter_evidence
    if not references_valid(refs, mapping):
        return "signal_references_invalid"
    if not issuer_valid(obj.company_name, refs, company):
        return "signal_issuer_not_grounded"
    if not obj.subject.strip() or not any(
        normalize(obj.subject) in normalize(r.quote) for r in obj.evidence
    ):
        return "signal_subject_not_grounded"
    for value in (obj.period_end, obj.event_date):
        if value and (
            value > source.available_at.date()
            or not any(value in dates_in(r.quote) for r in obj.evidence)
        ):
            return "signal_date_not_grounded"
    quote = fold(" ".join(r.quote for r in obj.evidence))
    spec = CATALOG[obj.kind]
    if not re.search(spec.terms, quote):
        return "signal_topic_not_grounded"
    if obj.assertion == "issue":
        if re.search(r"olabilir|ihtimal|olasilik|risk yonetimi|halinde|durumunda", quote):
            return "signal_hypothetical_not_specific_issue"
        if not re.search(spec.issue, quote):
            return "signal_issue_not_explicit"
        if re.search(
            r"soz konusu degil|dogru degil|tahsil edilememe.{0,30}bulunmamak|"
            r"vadesi gecmis.{0,35}bulunmamak|temerrut.{0,20}bulunmamak|"
            r"amac.{0,20}disinda kullanilmamis|risk bulunmamak|iptal edilmemis|"
            r"sinirli olumlu gorus verilmemis|degerleme yapilmadigi iddiasi|"
            r"(?:tahsil edilemeyen|vadesi gecen|vadesi gecmis|amac disi kullanim).{0,70}"
            r"(?:bulunmamak|bulunma|yoktur|mevcut degil)|nakit akis.{0,30}negatif degil",
            quote,
        ):
            return "signal_issue_negated_or_contested"
        if obj.kind == "insider_sales" and (
            not re.search(r"olumlu|buyume|basarili|guclu", quote)
            or re.search(r"tipe donus|virman|satis gerceklesme", quote)
        ):
            return "signal_insider_narrative_or_sale_unverified"
        if obj.kind == "report_consistency" and len({r.block_id for r in obj.evidence}) < 2:
            if not re.search(r"sehven|hatali|duzelt|yanlis", quote):
                return "signal_comparison_needs_two_spans"
        if obj.kind == "audit_specific" and source.kind not in {
            "financial",
            "financial_attachment",
        }:
            return "signal_auditor_source_unverified"
        if obj.kind == "audit_specific" and (
            obj.statement_type != "auditor_statement"
            or re.search(r"durumunda|gerektiginde|sorumlu|olasilik|ihtimal|garanti etme", quote)
        ):
            return "signal_generic_audit_text"
    # A regulatory/court finding must not be relabelled as a new company indicator.
    if obj.statement_type in {"regulatory_action", "court_decision"} and not re.search(
        r"spk|sermaye piyasasi kurulu|mahkeme|yargitay|karar|islem yasagi", quote
    ):
        return "signal_authority_not_grounded"
    if obj.statement_type == "issuer_statement" and re.search(
        r"su[c]? duyurusu|ceza davasi|mahkeme|iddianame|savcilik|iddia edilm|iddia olun",
        quote,
    ):
        return "signal_legal_statement_mislabelled"
    return None


def evaluate_signal_observations(analysis):
    findings, seen = [], set()
    for obj in analysis.signals:
        key = obj.model_dump_json()
        if key in seen:
            continue
        seen.add(key)
        spec = CATALOG[obj.kind]
        authority = obj.statement_type in {"regulatory_action", "court_decision"}
        review = (
            obj.assertion == "issue"
            and not authority
            and obj.statement_type != "allegation"
            and (obj.period_end is not None or obj.event_date is not None)
        )
        findings.append(
            ReviewFinding(
                id="SIG-" + digest(key.encode())[:16],
                rule_id="S-" + obj.kind,
                domain=spec.domain,
                level="review" if review else "context",
                title=spec.title + ": " + obj.subject,
                explanation=(
                    "Kaynakta belirli bir sorun beyanı var; alıntı doğrulandı, anlamı bağımsız teyit edilmedi. "
                    "Kalibrasyonsuz yeni inceleme adayı genel sonuca oy vermez."
                    if review
                    else "Kaynaklı karşı açıklama, belirsizlik, iddia veya bilinen karar bağlamı; yeni risk oyu değildir."
                ),
                evidence=obj.evidence,
                counter_evidence=obj.counter_evidence,
                unknowns=[
                    spec.missing,
                    "Belge beyanı bağımsız gerçeklik veya suç tespiti değildir.",
                ],
                origin="known_regulatory" if authority else "indicator",
                contributes_to_outcome=False,
            )
        )
    return findings


def measure_investor_signals(current, previous, facts):
    """Ratios describe exposure. Magnitude alone never proves abusive terms or overdue debt."""
    metrics = []

    def add(ident, domain, value, formula, inputs, unit="ratio"):
        metrics.append(
            Metric(
                id=ident,
                domain=domain,
                value=value,
                unit=unit,
                formula=formula,
                fact_ids=[f.id for f in inputs],
                source_ids=sorted({f.source_id for f in inputs}),
            )
        )

    assets = current.get("total_assets")
    for maturity in ("current", "noncurrent"):
        related = [
            current.get(maturity + "_" + key)
            for key in ("related_trade_receivables", "related_other_receivables")
        ]
        # Do not call one available component the complete related balance.
        if assets and assets.value > 0 and all(f is not None for f in related):
            add(
                maturity + "_related_receivables_assets",
                "relations",
                sum(f.value for f in related) / assets.value,
                f"({maturity}_related_trade_receivables + {maturity}_related_other_receivables) / total_assets",
                [*related, assets],
            )
    revenue, profit = current.get("revenue"), current.get("pretax_profit")
    annual = {}
    for fact in facts:
        if (
            fact.concept in {"net_income", "operating_cash_flow"}
            and fact.period_start == date(fact.period_end.year, 1, 1)
            and (fact.period_end.month, fact.period_end.day) == (12, 31)
        ):
            annual.setdefault((fact.period_start, fact.period_end), {})[fact.concept] = fact
    pairs = [p for p in annual.values() if {"net_income", "operating_cash_flow"} <= p.keys()]
    if len(pairs) >= 2:
        add(
            "cash_conversion_mismatch_periods",
            "financial",
            Decimal(
                sum(p["net_income"].value > 0 and p["operating_cash_flow"].value < 0 for p in pairs)
            ),
            "count(comparable annual periods with net_income > 0 and operating_cash_flow < 0); not persistence proof alone",
            [f for p in pairs for f in p.values()],
            "periods",
        )
    if profit and profit.value > 0:
        for concept in ("operating_profit", "investment_income"):
            fact = current.get(concept)
            if fact:
                add(
                    concept + "_pretax",
                    "financial",
                    fact.value / profit.value,
                    f"{concept} / pretax_profit; not a fraud or normalized-profit measure",
                    [fact, profit],
                )
    if revenue and revenue.value > 0:
        receivable = current.get("receivables")
        opening_receivable = next(
            (
                f
                for f in facts
                if f.concept == "receivables"
                and revenue.period_start
                and f.period_end.toordinal() == revenue.period_start.toordinal() - 1
            ),
            None,
        )
        if receivable and opening_receivable:
            days = Decimal((revenue.period_end - revenue.period_start).days + 1)
            add(
                "receivable_average_days",
                "financial",
                (receivable.value + opening_receivable.value) / 2 / revenue.value * days,
                "mean(opening_receivables, closing_receivables) / revenue * period_days; not actual invoice ageing",
                [opening_receivable, receivable, revenue],
                "days",
            )
        for maturity in ("current", "noncurrent"):
            asset = current.get(maturity + "_contract_assets")
            if asset:
                add(
                    maturity + "_contract_assets_revenue",
                    "financial",
                    asset.value / revenue.value,
                    f"{maturity}_contract_assets / period_revenue",
                    [asset, revenue],
                )
        inventory, old_inventory, cost = (
            current.get("inventories"),
            previous.get("inventories"),
            current.get("cost_of_sales"),
        )
        opening = next(
            (
                f
                for f in facts
                if f.concept == "inventories"
                and revenue.period_start
                and f.period_end.toordinal() == revenue.period_start.toordinal() - 1
            ),
            None,
        )
        if inventory and opening and cost and cost.value != 0 and revenue.period_start:
            days = Decimal((revenue.period_end - revenue.period_start).days + 1)
            add(
                "inventory_days",
                "financial",
                (opening.value + inventory.value) / 2 / abs(cost.value) * days,
                "mean(opening_inventory, closing_inventory) / abs(period_cost_of_sales) * period_days; proxy",
                [opening, inventory, cost],
                "days",
            )
        old_revenue = previous.get("revenue")
        if (
            inventory
            and old_inventory
            and old_inventory.value > 0
            and old_revenue
            and old_revenue.value > 0
        ):
            add(
                "inventory_growth_gap",
                "financial",
                inventory.value / old_inventory.value - revenue.value / old_revenue.value,
                "inventory_growth - comparable_revenue_growth; seasonal context required",
                [inventory, old_inventory, revenue, old_revenue],
            )
    ocf, adjustment = (
        current.get("operating_cash_flow"),
        current.get("cashflow_investment_adjustment"),
    )
    if ocf and adjustment and ocf.value != 0:
        add(
            "cashflow_investment_adjustment_share",
            "financial",
            abs(adjustment.value / ocf.value),
            "abs(investment_related_reconciliation_adjustment / reported_operating_cash_flow)",
            [adjustment, ocf],
        )
        add(
            "cashflow_without_investment_line_sensitivity",
            "financial",
            ocf.value - adjustment.value,
            "reported_operating_cash_flow - investment_related_adjustment; arithmetic sensitivity ONLY, not corrected OCF",
            [ocf, adjustment],
            "sensitivity_TRY_not_corrected_cashflow",
        )
    return metrics


def signal_checks(analysis, findings, coverage):
    checks, metric_ids = [], {m.id for m in analysis.metrics}
    for kind, spec in CATALOG.items():
        selected = [f for f in findings if f.rule_id == "S-" + kind or f.rule_id in spec.rules]
        used = [m for m in spec.metrics if m in metric_ids]
        if kind == "audit_specific":
            selected += [f for f in findings if f.rule_id.startswith("A-")]
        if kind == "related_terms":
            selected += [
                f
                for f in findings
                if f.rule_id == "R-OBS" or f.title == "İlişkili işlem / yönetici bağlantısı"
            ]
        checks.append(
            SignalCheck(
                id=kind,
                title=spec.title,
                domain=spec.domain,
                status="evidence_found" if selected else "partial" if used else "unavailable",
                finding_ids=list(dict.fromkeys(f.id for f in selected)),
                metric_ids=used,
                missing_inputs=[spec.missing],
                note=(
                    "Alıntı/ölçüm mevcut; tam mekanizma ve tahmin başarısı doğrulanmadı. "
                    if selected or used
                    else "Bu gözlem için yeterli doğrulanmış girdi bulunamadı; işaret yok sonucu değildir. "
                )
                + f"Alan kapsamı: {coverage.get(spec.domain, 'unavailable')}. "
                + (
                    "Günlük fiyat/hacimden bu kontrol hesaplanmaz; gün içi/emir veri hattı bağlı değil."
                    if kind in {"closing_pattern", "order_cancellations"}
                    else ""
                ),
            )
        )
    return checks
