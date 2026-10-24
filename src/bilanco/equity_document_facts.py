"""Neutral source facts and explicit comparisons; no company-specific risk shortcuts."""

import json
import re
from collections import defaultdict
from decimal import Decimal

from .documents import normalize
from .equity_models import (
    EvidenceComparison,
    FinancialHistoryPoint,
    FundExposure,
    Metric,
    ReviewFinding,
    cutoff,
)
from .equity_sources import fold
from .equity_tables import NUMBER, dates_in, parse_turkish
from .storage import digest

PATTERNS = {
    "fund_position": r"fon|yatirim",
    "fund_net_assets": r"fon.{0,45}(?:toplam deger|net varlik)|toplam fon deger",
    "fund_redemption_days": r"iade|geri alim|satis.{0,30}valor|nakde donus",
    "proceeds_plan": r"halka arz|fon kullanim|sermaye artir",
    "proceeds_spent": r"halka arz|fon kullanim|sermaye artir",
    "contract_owner": r"sozlesme|is ortakligi",
}


def fact_id(obj):
    return (
        "DOC-"
        + digest(
            json.dumps(obj.model_dump(mode="json"), sort_keys=True, ensure_ascii=False).encode()
        )[:16]
    )


def document_fact_error(
    obj, mapping, source, company, *, references_valid, issuer_valid, contains_name
):
    refs = obj.evidence + obj.counter_evidence
    if not references_valid(obj.evidence, mapping) or (
        obj.counter_evidence and not references_valid(obj.counter_evidence, mapping)
    ):
        return "document_fact_references_invalid"
    if any(mapping[r.block_id].source_id != source.id for r in refs):
        return "document_fact_cross_source_packet"
    if not issuer_valid(obj.entity_name, obj.evidence, company):
        return "document_fact_entity_not_grounded"
    if not contains_name(obj.subject, obj.evidence):
        return "document_fact_subject_not_grounded"
    text = fold(" ".join(r.quote for r in obj.evidence))
    if obj.statement_type in {"allegation", "regulatory_action", "court_decision"} or re.search(
        r"mahkeme|yargitay|suc duyurusu|iddianame|spk.{0,30}karar", text
    ):
        return "document_fact_not_predictive_source"
    if not re.search(PATTERNS[obj.kind], text):
        return "document_fact_kind_not_grounded"
    for name in ("period_start", "period_end", "effective_date", "basis_date"):
        value = getattr(obj, name)
        if value and not any(value in dates_in(r.quote) for r in obj.evidence):
            return "document_fact_date_not_grounded"
        if (
            value
            and value > source.available_at.date()
            and not (obj.kind == "proceeds_plan" and name in {"period_start", "period_end"})
        ):
            return "document_fact_future_observation"
    if obj.period_start and obj.period_end and obj.period_start > obj.period_end:
        return "document_fact_invalid_period"
    if obj.kind == "proceeds_plan" and not re.search(r"plan|tahmin|hedef|ongoru", text):
        return "document_fact_target_not_grounded"
    if obj.kind == "proceeds_spent" and (
        not re.search(r"kullanil|harcan|gercekles", text)
        or re.search(r"kullanilacak|harcanacak|planlan|ongorul", text)
    ):
        return "document_fact_realization_not_grounded"
    fund_kind = obj.kind.startswith("fund_")
    if fund_kind and not re.fullmatch(r"[A-Z0-9]{3,5}", obj.subject):
        return "document_fact_fund_code_not_explicit"
    if obj.kind in {"fund_net_assets", "fund_redemption_days"} and (
        source.role != "related_fund" or source.entity_code != obj.subject
    ):
        return "document_fact_fund_source_unverified"
    if obj.kind not in {"fund_net_assets", "fund_redemption_days"} and source.role != "issuer":
        return "document_fact_wrong_source_role"
    if obj.kind == "fund_position" and not re.search(
        r"finansal yatirim|fon katilma pay|fona yapilan yatirim|fonuna yatirim", text
    ):
        return "document_fact_fund_direction_unverified"
    if obj.kind == "contract_owner":
        if not obj.counterparty or not contains_name(obj.counterparty, obj.evidence):
            return "document_fact_owner_not_grounded"
        party = re.escape(fold(obj.counterparty))
        role = r"(?:sozlesmenin tarafi(?:dir)?|sozlesmeyi imzalamistir|is ortakliginda yer alan)"
        if not re.search(party + r".{0,100}" + role + "|" + role + r".{0,180}" + party, text):
            return "document_fact_owner_role_not_explicit"
        if re.search(r"tarafi degil|imzalamamis|imzalamadi|imzalamamistir", text):
            return "document_fact_owner_negated"
        if obj.value_text is not None or obj.currency is not None:
            return "document_fact_text_has_amount"
        return None
    if obj.value_text is None or obj.value_evidence is None:
        return "document_fact_value_missing"
    if not references_valid([obj.value_evidence], mapping) or not any(
        obj.value_evidence.block_id == ref.block_id
        and normalize(obj.value_evidence.quote) in normalize(ref.quote)
        for ref in obj.evidence
    ):
        return "document_fact_value_span_invalid"
    if obj.kind in {"fund_position", "proceeds_plan", "proceeds_spent"} and not contains_name(
        obj.subject, [obj.value_evidence]
    ):
        return "document_fact_value_subject_mismatch"
    if obj.kind in {"fund_net_assets", "fund_redemption_days"} and not re.search(
        PATTERNS[obj.kind], fold(obj.value_evidence.quote)
    ):
        return "document_fact_value_kind_mismatch"
    if obj.value_text not in NUMBER.findall(obj.value_evidence.quote):
        return "document_fact_value_not_grounded"
    value_span = obj.value_evidence.quote.replace(obj.subject, "")
    value_span = re.sub(r"\d{2}\.\d{2}\.\d{4}", "", value_span)
    # A list bullet is not a negative amount; a later dash is a missing cell,
    # never zero. Multiple table cells need an explicitly ordered date header.
    value_span = re.sub(r"^\s*[—–-]\s+(?=[^\W\d_])", "", value_span)
    cells = NUMBER.findall(value_span)
    if len(cells) != 1:
        columns = []
        for ref in obj.evidence:
            if (
                ref.block_id != obj.value_evidence.block_id
                or obj.value_evidence.quote not in ref.quote
            ):
                continue
            preceding = ref.quote.split(obj.value_evidence.quote, 1)[0]
            for line in preceding.splitlines():
                header = dates_in(line)
                if (
                    len(header) == len(cells)
                    and len(set(header)) == len(header)
                    and len({(d.month, d.day) for d in header}) == 1
                ):
                    columns = header
        if not columns or obj.period_end not in columns:
            return "document_fact_value_span_ambiguous"
        if cells[columns.index(obj.period_end)] != obj.value_text:
            return "document_fact_value_period_mismatch"
    try:
        value = parse_turkish(obj.value_text)
    except ValueError:
        return "document_fact_value_invalid"
    if value < 0:
        return "document_fact_negative_value"
    if re.search(r"\b(?:bin|milyon|milyar)\b|%", fold(obj.value_evidence.quote)):
        return "document_fact_scaled_or_percentage_value"
    if obj.kind == "fund_redemption_days":
        if (
            obj.currency
            or value != value.to_integral_value()
            or value > 365
            or not re.search(r"\bgun(?:u)?\b", text)
        ):
            return "document_fact_redemption_unit_invalid"
        if obj.day_basis == "unknown" or not re.search(
            "is gunu" if obj.day_basis == "business" else "takvim gunu", text
        ):
            return "document_fact_redemption_day_basis_unknown"
    else:
        units = {
            "TRY": r"\btl\b|turk lirasi|\btry\b",
            "USD": r"\busd\b|abd dolari",
            "EUR": r"\beur\b|avro|euro",
        }
        if obj.currency not in units or not re.search(units[obj.currency], text):
            return "document_fact_currency_not_grounded"
    if obj.measurement_basis == "inflation_adjusted" and (
        obj.basis_date is None or not re.search(r"satin alma gucu|tms 29|enflasyona gore", text)
    ):
        return "document_fact_basis_not_grounded"
    if obj.measurement_basis == "nominal" and not re.search(
        r"nominal|enflasyon.{0,30}uygulanma|fon toplam deger|fon net varlik", text
    ):
        return "document_fact_nominal_not_grounded"
    if obj.scope == "standalone" and not re.search(r"konsolide olmayan|konsolide degil|solo", text):
        return "document_fact_scope_not_grounded"
    if obj.scope == "consolidated" and (
        not re.search(r"\bkonsolide\b", text)
        or re.search(r"konsolide olmayan|konsolide degil", text)
    ):
        return "document_fact_scope_not_grounded"
    if obj.scope == "fund" and source.role != "related_fund":
        return "document_fact_scope_not_grounded"
    return None


def analyze_documents(analysis):
    """Derive calculations only from revalidated, in-cutoff inputs and retain unknowns."""
    # Imported lazily to keep extraction and comparison independently testable.
    from .equity_text import contains_name, issuer_valid, references_valid

    sources = {s.id: s for s in analysis.sources if s.available_at <= cutoff(analysis.as_of)}
    blocks = {b.id: b for b in analysis.blocks if b.source_id in sources}
    accepted = {}
    for obj in analysis.document_facts:
        source_ids = {blocks[r.block_id].source_id for r in obj.evidence if r.block_id in blocks}
        if len(source_ids) != 1:
            continue
        source = sources[next(iter(source_ids))]
        company = source.entity_name or analysis.company
        if (
            document_fact_error(
                obj,
                blocks,
                source,
                company,
                references_valid=references_valid,
                issuer_valid=issuer_valid,
                contains_name=contains_name,
            )
            is None
        ):
            accepted[fact_id(obj)] = obj
    metrics, findings, comparisons, exposures = [], [], [], []

    def refs(items, name="evidence"):
        return list(
            {(r.block_id, r.quote): r for obj in items for r in getattr(obj, name)}.values()
        )

    def source_ids(items):
        return sorted({blocks[r.block_id].source_id for r in refs(items)})

    def metric(name, value, items, formula):
        metrics.append(
            Metric(
                id=name,
                domain="financial",
                value=value,
                unit="ratio",
                formula=formula,
                fact_ids=[fact_id(o) for o in items],
                source_ids=source_ids(items),
            )
        )
        return name

    def comparison(kind, items, status, explanation, used=(), missing=()):
        ident = "CMP-" + digest(repr((kind, sorted(fact_id(o) for o in items))).encode())[:16]
        obj = EvidenceComparison(
            id=ident,
            kind=kind,
            subject=items[0].subject,
            status=status,
            input_ids=[fact_id(o) for o in items],
            metric_ids=list(used),
            explanation=explanation,
            evidence=refs(items),
            counter_evidence=refs(items, "counter_evidence"),
            missing_inputs=list(missing),
        )
        comparisons.append(obj)
        if status == "difference":
            findings.append(
                ReviewFinding(
                    id=ident,
                    rule_id="D-" + kind,
                    domain="operations",
                    level="review",
                    title="Belgeler arasında incelenecek fark: " + items[0].subject,
                    explanation=explanation
                    + " Fark tek başına ihlal veya dolandırıcılık tespiti değildir; yeni kontrol kalibre edilmedi.",
                    metric_ids=list(used),
                    evidence=obj.evidence,
                    counter_evidence=obj.counter_evidence,
                    unknowns=[
                        "Değişiklik izni, ekonomik gerekçe ve kaynak beyanının bağımsız teyidi."
                    ],
                    contributes_to_outcome=False,
                )
            )

    groups = defaultdict(list)
    for obj in accepted.values():
        groups[fold(obj.subject)].append(obj)
    for items in groups.values():
        plans = [o for o in items if o.kind == "proceeds_plan"]
        spent = [o for o in items if o.kind == "proceeds_spent"]
        for plan in plans:
            for actual in spent:
                pair = [plan, actual]
                # No annual-vs-nine-month, currency, scope or restatement shortcuts.
                compatible = (
                    plan.period_start is not None
                    and plan.period_end is not None
                    and (
                        plan.period_start,
                        plan.period_end,
                        plan.currency,
                        plan.scope,
                        plan.measurement_basis,
                        plan.basis_date,
                    )
                    == (
                        actual.period_start,
                        actual.period_end,
                        actual.currency,
                        actual.scope,
                        actual.measurement_basis,
                        actual.basis_date,
                    )
                    and plan.scope != "unknown"
                    and plan.measurement_basis != "unknown"
                    and len(set(source_ids(pair))) >= 2
                    and sources[source_ids([plan])[0]].available_at.date() < plan.period_end
                )
                if not compatible:
                    comparison(
                        "proceeds",
                        pair,
                        "not_comparable",
                        "Plan ve gerçekleşme aynı dönem/baz/kapsamda veya bağımsız kaynaklarda değil.",
                        missing=[
                            "Aynı dönem, para birimi, kapsam, ölçüm esası ve tarihli ilk plan."
                        ],
                    )
                    continue
                expected, realized = (
                    parse_turkish(plan.value_text),
                    parse_turkish(actual.value_text),
                )
                if expected <= 0:
                    comparison(
                        "proceeds", pair, "not_comparable", "Pozitif plan tutarı bulunmuyor."
                    )
                    continue
                mid = metric(
                    "proceeds_ratio_" + fact_id(actual)[4:] + "_" + fact_id(plan)[4:],
                    realized / expected,
                    pair,
                    "actual_proceeds_use / original_planned_use; not a violation probability",
                )
                tolerance = (
                    Decimal(1).scaleb(expected.as_tuple().exponent)
                    + Decimal(1).scaleb(realized.as_tuple().exponent)
                ) / 2
                difference = abs(realized - expected) > tolerance
                revised = any(
                    fold(plan.subject) in fold(r.quote)
                    and re.search(
                        r"revize edilmistir|guncellenmistir|degisikligi onaylanmistir",
                        fold(r.quote),
                    )
                    and not re.search(
                        r"olabilir|planlan|beklen|onaylanmamis|guncellenmemis", fold(r.quote)
                    )
                    for r in refs(pair, "counter_evidence")
                )
                comparison(
                    "proceeds",
                    pair,
                    "context"
                    if revised and difference
                    else "difference"
                    if difference
                    else "consistent",
                    f"Aynı dönem için plan {expected}, gerçekleşme {realized} {plan.currency}; basılı tutar yuvarlama toleransı {tolerance}. Eksik veya fazla kullanımın nedeni ayrıca incelenmeli.",
                    [mid],
                )
                if revised and difference:
                    comparisons[
                        -1
                    ].explanation += " Aynı proje için açık plan güncellemesi/onay beyanı var; eski plana fark otomatik sorun sayılmadı."
        owners = [o for o in items if o.kind == "contract_owner" and o.period_end is not None]
        for index, left in enumerate(owners):
            for right in owners[index + 1 :]:
                if left.period_end != right.period_end or len(set(source_ids([left, right]))) < 2:
                    continue
                changed = fold(left.counterparty) != fold(right.counterparty)
                comparison(
                    "contract_party",
                    [left, right],
                    "difference" if changed else "consistent",
                    f"Aynı sözleşme/dönem için belirtilen taraflar: {left.counterparty}; {right.counterparty}. Devir veya düzeltme olabilir; listedeki şirkete gelir atfı doğrulanmalı.",
                )
        positions = [o for o in items if o.kind == "fund_position" and o.period_end is not None]
        for position in positions:
            mids, missing = [], []
            assets = [
                f
                for f in analysis.facts
                if f.source_id in sources
                and sources[f.source_id].role == "issuer"
                and f.concept == "total_assets"
                and f.period_start is None
                and f.period_end == position.period_end
                and f.currency == position.currency
                and f.scope == position.scope
                and position.measurement_basis != "unknown"
                and (
                    (
                        f.measurement_basis == position.measurement_basis
                        and f.basis_date == position.basis_date
                    )
                    or f.basis_date == position.period_end
                    and position.basis_date in (None, position.period_end)
                    and position.measurement_basis == "nominal"
                )
            ]
            asset_values = {f.value for f in assets}
            if len(asset_values) == 1 and next(iter(asset_values)) > 0:
                base = assets[0]
                name = metric(
                    "fund_position_assets_" + fact_id(position)[4:],
                    parse_turkish(position.value_text) / base.value,
                    [position],
                    "disclosed_fund_position / same_date_issuer_total_assets; exposure, not a loss or fraud score",
                )
                metrics[-1].fact_ids.append(base.id)
                metrics[-1].source_ids = sorted(set(metrics[-1].source_ids + [base.source_id]))
                mids.append(name)
            else:
                missing.append(
                    "Şirket varlıklarına oran için aynı kapsam/tarih/bazda tekil toplam varlık."
                )
            linked = [
                s
                for s in sources.values()
                if s.role == "related_fund" and s.entity_code == position.subject
            ]
            totals = [
                o
                for o in items
                if o.kind == "fund_net_assets"
                and o.period_end == position.period_end
                and o.currency == position.currency
                and o.value_text is not None
            ]
            # A period-end nominal NAV and a carrying value at the same purchasing-power
            # date can be compared; an older nominal NAV cannot be restated by guessing.
            totals = [
                o
                for o in totals
                if position.scope in {"standalone", "consolidated"}
                and position.measurement_basis != "unknown"
                and o.scope == "fund"
                and (
                    o.measurement_basis == position.measurement_basis
                    and o.basis_date == position.basis_date
                    or o.measurement_basis == "nominal"
                    and o.basis_date in (None, o.period_end)
                    and position.basis_date == position.period_end
                )
            ]
            values = {parse_turkish(o.value_text) for o in totals}
            if len(values) == 1 and next(iter(values)) > 0:
                total = totals[0]
                share = parse_turkish(position.value_text) / parse_turkish(total.value_text)
                mids.append(
                    metric(
                        "fund_position_nav_" + fact_id(position)[4:],
                        share,
                        [position, total],
                        "issuer_carrying_value / same_date_fund_NAV; valuation exposure proxy, NOT verified ownership",
                    )
                )
                if share > 1:
                    missing.append(
                        "Pozisyon fon toplamını aşıyor; değerleme/kapsam uyuşmazlığı çözülmeli."
                    )
            else:
                missing.append("Aynı tarih/para birimi/değerleme bazında tekil fon toplam değeri.")
            terms = [
                o
                for o in items
                if o.kind == "fund_redemption_days"
                and o.effective_date
                and o.effective_date <= position.period_end
            ]
            terms.sort(key=lambda o: o.effective_date, reverse=True)
            latest = (
                [o for o in terms if o.effective_date == terms[0].effective_date] if terms else []
            )
            term_values = {parse_turkish(o.value_text) for o in latest}
            days = next(iter(term_values)) if len(term_values) == 1 else None
            if days is None:
                missing.append("Pozisyon tarihinde geçerli, çelişkisiz iade/valör şartları.")
            missing += [
                "Alt fon/varlıkların tam tarihli dökümü ve bağımsız değerleme teyidi.",
                "Yakın borç vadeleri, blokajlar ve pozisyona uygulanabilen nakde dönüş koşulları.",
            ]
            exposures.append(
                FundExposure(
                    code=position.subject,
                    period_end=position.period_end,
                    position_ids=[fact_id(position)],
                    related_source_ids=[s.id for s in linked],
                    metric_ids=mids,
                    redemption_days=days,
                    redemption_day_basis=latest[0].day_basis if days is not None else "unknown",
                    missing_inputs=missing,
                    note="Yön: şirket → fon. Fona yatırım yapmak, fonun şirket hissesini alması veya tek kişinin kontrolü demek değildir. Fon nakitle eşit kabul edilmedi.",
                )
            )
    return metrics, findings, comparisons, exposures


def financial_history(analysis):
    """First available compatible observations; do not sum YTD quarters or restated levels."""
    sources = {
        s.id: s
        for s in analysis.sources
        if s.role == "issuer" and s.available_at <= cutoff(analysis.as_of)
    }
    groups = defaultdict(list)
    for fact in analysis.facts:
        if fact.source_id in sources and fact.period_start and fact.period_end <= analysis.as_of:
            key = (fact.period_start, fact.period_end, fact.scope, fact.currency)
            groups[key].append(fact)
    points = []
    for (start, end, scope, _), facts in sorted(groups.items()):
        # A pair must come from the same disclosure/basis; no oldest-profit/latest-cash joins.
        candidates = defaultdict(list)
        for f in facts:
            s = sources[f.source_id]
            candidates[(s.disclosure_id or s.id, f.basis_date, f.measurement_basis)].append(f)
        snapshots = sorted(
            candidates.values(), key=lambda fs: min(sources[f.source_id].available_at for f in fs)
        )
        chosen = next(
            (
                fs
                for fs in snapshots
                if {"net_income", "operating_cash_flow"} <= {f.concept for f in fs}
            ),
            snapshots[0],
        )
        values = {
            kind: {f.value for f in chosen if f.concept == kind}
            for kind in ("net_income", "operating_cash_flow")
        }
        known = all(len(v) == 1 for v in values.values())
        profit = next(iter(values["net_income"])) if known else None
        cash = next(iter(values["operating_cash_flow"])) if known else None
        points.append(
            FinancialHistoryPoint(
                period_start=start,
                period_end=end,
                scope=scope,
                source_ids=sorted({f.source_id for f in chosen}),
                fact_ids=[f.id for f in chosen],
                cash_profit=cash / profit if known and profit > 0 else None,
                profit_positive_cash_negative=profit > 0 and cash < 0 if known else None,
                note="İlk kullanılabilir uyumlu rapor çifti. Birikimli çeyrekler toplanmadı; farklı bazların parasal seviyeleri karşılaştırılmadı. Negatif nakit tek başına usulsüzlük değildir.",
            )
        )
    return points
