"""Conservative Turkish statement reader: no guessed dates, units or empty cells."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .equity_models import EquitySource, FinancialFact
from .equity_sources import fold
from .models import Block, Locator
from .storage import digest

DATE = re.compile(r"\b\d{2}\.\d{2}\.20\d{2}\b")
NUMBER = re.compile(r"\(?-?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?\)?|[—–-]")
CONCEPTS = {
    "cash": ("balance", r"nakit ve nakit benzerleri"),
    "current_assets": ("balance", r"(?:toplam )?donen varliklar"),
    "current_liabilities": ("balance", r"(?:toplam )?kisa vadeli yukumlulukler"),
    "total_assets": ("balance", r"toplam varliklar"),
    "total_liabilities": ("balance", r"toplam yukumlulukler"),
    "equity": ("balance", r"(?:toplam )?ozkaynaklar"),
    "short_debt": ("balance", r"kisa vadeli borclanmalar"),
    "current_long_debt": ("balance", r"uzun vadeli borclanmalarin kisa vadeli kisimlari"),
    "long_debt": ("balance", r"uzun vadeli borclanmalar"),
    "receivables": ("balance", r"ticari alacaklar"),
    "related_trade_receivables": ("balance", r"-?\s*iliskili taraflardan ticari alacaklar"),
    "related_other_receivables": ("balance", r"-?\s*iliskili taraflardan diger alacaklar"),
    "inventories": ("balance", r"stoklar"),
    "contract_assets": ("balance", r"(?:musteri sozlesmelerinden dogan )?sozlesme varliklari"),
    "financial_investments": ("balance", r"finansal yatirimlar"),
    "paid_capital": ("balance", r"odenmis sermaye"),
    "revenue": ("income", r"hasilat|satis gelirleri|net satislar"),
    "cost_of_sales": ("income", r"satislarin maliyeti"),
    "operating_profit": ("income", r"esas faaliyet kari(?: \(?zarari\)?| zarari)"),
    "net_income": ("income", r"donem kari \(?zarari\)?"),
    "financing_expense": ("income", r"finansman giderleri"),
    "investment_income": ("income", r"yatirim faaliyetlerinden gelirler"),
    "monetary_gain": ("income", r"net parasal pozisyon kazanclari \(?kayiplari\)?"),
    "pretax_profit": ("income", r"surdurulen faaliyetler vergi oncesi kari \(?zarari\)?"),
    "operating_cash_flow": ("cashflow", r"isletme faaliyetlerinden nakit akislari"),
    "cashflow_investment_adjustment": (
        "cashflow",
        r"yatirim ya da finansman faaliyetlerinden kaynaklanan nakit akislarina neden olan diger kalemlere iliskin duzeltmeler",
    ),
    "capex": (
        "cashflow",
        r"maddi ve maddi olmayan duran varliklarin alimindan kaynaklanan nakit cikislari",
    ),
}


def parse_turkish(raw: str) -> Decimal:
    value = raw.strip()
    if not re.fullmatch(r"\(?-?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?\)?", value):
        raise ValueError("Belirsiz Türkçe sayı veya boş hücre.")
    if value.startswith("(") != value.endswith(")"):
        raise ValueError("Dengesiz parantez.")
    if value.startswith("("):
        value = "-" + value[1:-1]
    result = Decimal(value.replace(".", "").replace(",", "."))
    if not result.is_finite():
        raise ValueError("Sonlu sayı gerekli.")
    return result


MONTHS = {
    name: i
    for i, name in enumerate(
        (
            "ocak",
            "subat",
            "mart",
            "nisan",
            "mayis",
            "haziran",
            "temmuz",
            "agustos",
            "eylul",
            "ekim",
            "kasim",
            "aralik",
        ),
        1,
    )
}
MONTH_PATTERN = "|".join(MONTHS)


def nominal_basis_refs(blocks):
    """Require an explicit cessation/non-application statement, never infer from year alone."""
    refs = []
    for block in blocks:
        for match in re.finditer(
            r"[^.!?\n]*(?:TMS\s*29|enflasyon)[^.!?\n]*(?:[.!?]|$)", block.text, re.I
        ):
            quote = match[0].strip()
            clean = fold(quote)
            if re.search(
                r"uygulanmamasina|uygulanmamistir|uygulanmamaktadir|uygulamasina son veril|"
                r"duzeltme(?:si)? yapilmamistir|duzeltmesine tabi tutulmamistir",
                clean,
            ):
                refs.append(Locator(block_id=block.id, quote=quote))
    return refs


def dates_in(text: str) -> list[date]:
    folded = fold(text)
    matches = [
        (m.start(), datetime.strptime(m[0], "%d.%m.%Y").date()) for m in DATE.finditer(folded)
    ]
    for m in re.finditer(rf"\b(\d{{1,2}}) ({MONTH_PATTERN}) (20\d{{2}})\b", folded):
        matches.append((m.start(), date(int(m[3]), MONTHS[m[2]], int(m[1]))))
    return [value for _, value in sorted(matches)]


def periods(header: str, flow: bool) -> list[tuple[date | None, date]]:
    # KAP prints all starts in one header row, then all corresponding ends.
    lines = header.splitlines()
    dated = [dates_in(line) for line in lines if dates_in(line)]
    if not dated:
        return []
    ends = dated[-1]
    if not 1 <= len(ends) <= (8 if flow else 4):
        return []
    if not flow:
        return [(None, end) for end in ends]
    dated_lines = [(line, dates_in(line)) for line in lines if dates_in(line)]
    if len(dated_lines) >= 4:
        tail = dated_lines[-4:]
        if (
            all(len(values) == 2 for _, values in tail)
            and all(line.rstrip().endswith(("-", "–")) for line, _ in tail[:2])
            and all("-" not in line and "–" not in line for line, _ in tail[2:])
        ):
            starts = tail[0][1] + tail[1][1]
            combined_ends = tail[2][1] + tail[3][1]
            if all(a.year == b.year and a <= b for a, b in zip(starts, combined_ends, strict=True)):
                return list(zip(starts, combined_ends, strict=True))
    if len(dated) >= 2 and len(dated[-2]) == len(ends):
        starts = dated[-2]
        if all(
            start.year == end.year and start <= end for start, end in zip(starts, ends, strict=True)
        ):
            return list(zip(starts, ends, strict=True))
    partial = [
        (day, fold(month))
        for line in lines
        if "hesap donemi" not in fold(line)
        for day, month in re.findall(r"\b(\d{1,2})\s+([^\W\d_]+)\s*[-–]", line)
        if fold(month) in MONTHS
    ]
    if len(partial) == len(ends):
        starts = [
            date(end.year, MONTHS[month], int(day))
            for (day, month), end in zip(partial, ends, strict=True)
        ]
        if all(a <= b for a, b in zip(starts, ends, strict=True)):
            return list(zip(starts, ends, strict=True))
    # Some PDF engines put a start/end pair in each column on one line.
    if len(ends) in (4, 8):
        pairs = list(zip(ends[::2], ends[1::2], strict=True))
        if all(a.year == b.year and a <= b for a, b in pairs):
            return pairs
    return []


def report_context(blocks: list[Block], issuer_identity: str | None = None):
    """Use explicit cover/table fields, never generic consolidation policy text."""
    scope_refs, basis_refs, inflation_refs = [], [], []
    scopes, bases = set(), set()
    primary = [
        b
        for b in blocks
        if any(
            re.search(r"tarihi itibariyla (?:konsolide )?finansal durum tablosu$", fold(line))
            or re.fullmatch(r"\d{2}\.\d{2}\.20\d{2} (?:donemi )?finansal rapor", fold(line))
            for line in b.text.splitlines()
        )
    ]
    primary_ids = {primary[0].id} if primary else {b.id for b in blocks}
    if issuer_identity and primary and issuer_identity not in fold(primary[0].text[:700]):
        return None, None, [], False
    for block in blocks:
        for line in block.text.splitlines():
            clean = fold(line)
            scope = None
            if re.fullmatch(r"konsolide olmayan(?: finansal tablolar)?", clean) or re.search(
                r"finansal tablo turu\s+solo(?: solo)*$", clean
            ):
                scope = "standalone"
            elif re.fullmatch(r"konsolide(?: finansal tablolar)?", clean) or re.search(
                r"finansal tablo (?:turu|niteligi)\s+konsolide(?: konsolide)*$|tarihi itibariyla konsolide finansal durum tablosu$",
                clean,
            ):
                scope = "consolidated"
            if scope:
                scopes.add(scope)
                scope_refs.append(Locator(block_id=block.id, quote=line))
            title = re.fullmatch(r"\d{2}\.\d{2}\.20\d{2} (?:donemi )?finansal rapor", clean)
            power = "satin alma gucu" in clean and (
                "tutarlar" in clean or "ifade edilmistir" in clean
            )
            if (title or power) and block.id in primary_ids:
                values = dates_in(line)
                if len(set(values)) == 1:
                    bases.add(values[0])
                    basis_refs.append(Locator(block_id=block.id, quote=line))
            if "tms 29" in clean or power:
                inflation_refs.append(Locator(block_id=block.id, quote=line))
    return (
        next(iter(scopes)) if len(scopes) == 1 else None,
        next(iter(bases)) if len(bases) == 1 else None,
        scope_refs[:1] + basis_refs[:1] + inflation_refs[:1],
        bool(inflation_refs),
    )


def extract_financial(
    source: EquitySource,
    blocks: list[Block],
    *,
    linked_blocks: list[Block] | None = None,
    issuer_identity: str | None = None,
) -> tuple[list[FinancialFact], list[dict]]:
    if source.kind not in {"financial", "financial_attachment"}:
        return [], []
    text = "\n".join(b.text for b in blocks)
    folded = fold(text)
    scope, basis, basis_refs, inflation = report_context(blocks, issuer_identity)
    nominal_refs = nominal_basis_refs(blocks)
    if basis is None and nominal_refs:
        # An old full appendix may have a dated balance-sheet heading instead of
        # the modern KAP "31.12.YYYY Finansal Rapor" cover field.
        for block in blocks:
            for line in block.text.splitlines():
                if re.search(
                    r"tarihi itibariyla (?:konsolide )?finansal durum tablosu$", fold(line)
                ):
                    values = dates_in(line)
                    if len(values) == 1 and values[0] < date(2023, 1, 1):
                        basis = values[0]
                        basis_refs.append(Locator(block_id=block.id, quote=line))
                        break
            if basis:
                break
    # Caller supplies ONLY same-disclosure dated financial siblings. Both period and
    # scope must agree before borrowing a missing inflation statement from the appendix.
    if linked_blocks:
        other_scope, other_basis, refs, other_inflation = report_context(
            linked_blocks, issuer_identity
        )
        if scope and basis and other_scope == scope and other_basis == basis:
            inflation = inflation or other_inflation
            basis_refs += refs
            nominal_refs += nominal_basis_refs(linked_blocks)
    rejected = []
    if not scope or not basis or basis > source.published_at.date():
        return [], [{"source_id": source.id, "reason": "scope_or_basis_unverified"}]
    # Legacy nominal reports are accepted only with explicit policy evidence and
    # before the modern inflation-reporting period. No relaxation of modern reports.
    nominal = basis < date(2023, 1, 1) and bool(nominal_refs)
    explicit_power = any(
        "satin alma gucu" in fold(ref.quote) and basis in dates_in(ref.quote) for ref in basis_refs
    )
    if nominal and explicit_power:
        return [], [{"source_id": source.id, "reason": "measurement_basis_conflict"}]
    if nominal_refs and not nominal and not explicit_power:
        return [], [{"source_id": source.id, "reason": "inflation_basis_unverified"}]
    if nominal:
        basis_refs += nominal_refs[:1]
    if not inflation and not nominal:
        return [], [{"source_id": source.id, "reason": "inflation_basis_unverified"}]
    measurement_basis = "nominal" if nominal else "inflation_adjusted"
    unit_context = fold(
        " ".join(
            line
            for line in text.splitlines()
            if re.search(r"tutarlar|sunum para birimi", fold(line))
        )
    )
    scale = (
        1_000_000
        if re.search(r"\bmilyon (?:tl|turk lirasi)", unit_context)
        else (1000 if re.search(r"\bbin (?:tl|turk lirasi)", unit_context) else 1)
    )
    currency_ok = bool(re.search(r"sunum para birimi\s+tl\b|turk lirasi|\(\s*tl\s*\)", folded))
    if not currency_ok:
        return [], [{"source_id": source.id, "reason": "currency_unverified"}]
    section, columns, header_ref = "", [], None
    maturity = "unknown"
    recent: list[str] = []
    facts = []
    for block in blocks:
        lines = block.text.splitlines()
        note_column = "dipnot" in fold(" ".join(lines[:12]))
        index = 0
        while index < len(lines):
            line = lines[index]
            clean = fold(line)
            # Full-report titles precede the dates; KAP summary titles follow them.
            full_section = None
            if re.search(r"tarihi itibariyla (?:konsolide )?finansal durum tablosu$", clean):
                full_section = "balance"
            elif re.search(r"hesap donemine ait (?:konsolide )?kar veya zarar tablosu", clean):
                full_section = "income"
            elif re.search(r"hesap donemine ait (?:konsolide )?nakit akis tablosu$", clean):
                full_section = "cashflow"
            if full_section:
                section = full_section
                columns, header_ref = [], Locator(block_id=block.id, quote=line)
                maturity = "unknown"
            if section == "balance":
                if re.match(r"(?:toplam )?donen varliklar(?:\s|$)", clean):
                    maturity = "current"
                elif re.match(r"(?:toplam )?duran varliklar(?:\s|$)", clean):
                    maturity = "noncurrent"
            if section and dates_in(line) and not full_section:
                candidate_columns = periods("\n".join([*recent[-12:], line]), section != "balance")
                if candidate_columns:
                    columns = candidate_columns
                    header_ref = Locator(block_id=block.id, quote=line)
            if re.fullmatch(r"finansal durum tablosu(?: bilanco)?", clean):
                section = "balance"
            elif clean == "kar veya zarar tablosu":
                section = "income"
            elif re.fullmatch(r"nakit akis tablosu(?: dolayli yontem| dogrudan yontem)?", clean):
                section = "cashflow"
            elif re.search(
                r"(?:^| )ozkaynaklar degisim tablosu$|^diger kapsamli gelir tablosu$|finansal tablolara iliskin (?:aciklayici )?dipnotlar$",
                clean,
            ):
                section = ""
            else:
                # Preserve wrapped labels but never join arbitrary numeric rows.
                if section:
                    for concept, (expected, pattern) in CONCEPTS.items():
                        if section != expected:
                            continue
                        joined = line
                        match = None
                        for width in (1, 2, 3, 4):
                            joined = " ".join(lines[index : index + width])
                            candidate = fold(joined)
                            # Match the folded label, slice by words using the original line.
                            match = re.match(rf"^(?:{pattern})\s+([\d(—–-].*)$", candidate)
                            if match:
                                break
                            if re.search(r"\d", joined):
                                break
                        if not match:
                            continue
                        # Fold removes minus/parens; extract from ORIGINAL suffix after the first digit.
                        # Labels in CONCEPTS have no digits. A printed dash is preserved separately.
                        start = re.search(r"\(?-?\d|[—–-](?=\s|$)", joined.lstrip("- "))
                        if not start:
                            continue
                        tail = joined.lstrip("- ")[start.start() :].strip()
                        values = NUMBER.findall(tail)
                        residue = NUMBER.sub("", tail).strip(" \t|:")
                        if (
                            len(values) == len(columns) + 1
                            and len(values[0]) <= 2
                            and (note_column or "dipnot" in fold(" ".join(recent)))
                        ):
                            values = values[1:]
                        if residue or len(values) != len(columns) or header_ref is None:
                            rejected.append(
                                {
                                    "source_id": source.id,
                                    "concept": concept,
                                    "reason": "ambiguous_columns",
                                    "row": joined,
                                }
                            )
                            break
                        for (begin, end), raw in zip(columns, values, strict=True):
                            if end > basis:
                                rejected.append({"reason": "future_period", "concept": concept})
                                continue
                            try:
                                value = parse_turkish(raw)
                            except (ValueError, InvalidOperation):
                                rejected.append(
                                    {"reason": "missing_cell", "concept": concept, "row": joined}
                                )
                                continue
                            ref = Locator(
                                block_id=block.id,
                                quote=joined
                                if width == 1
                                else "\n".join(lines[index : index + width]),
                            )
                            facts.append(
                                FinancialFact(
                                    id=digest(
                                        f"{source.id}:{concept}:{maturity}:{begin}:{end}:{value}".encode()
                                    )[:24],
                                    source_id=source.id,
                                    concept=concept,
                                    period_start=begin,
                                    period_end=end,
                                    basis_date=basis,
                                    scope=scope,
                                    currency="TRY",
                                    value=value * scale,
                                    scale=scale,
                                    evidence=ref,
                                    header_evidence=header_ref,
                                    maturity=maturity
                                    if concept
                                    in {
                                        "financial_investments",
                                        "related_trade_receivables",
                                        "related_other_receivables",
                                        "contract_assets",
                                    }
                                    else "unknown",
                                    basis_evidence=basis_refs,
                                    measurement_basis=measurement_basis,
                                )
                            )
                        index += width - 1
                        break
                recent.append(line)
                recent = recent[-15:]
                index += 1
                continue
            if section:
                header = "\n".join(recent[-12:])
                columns = periods(header, section != "balance")
                header_ref = Locator(block_id=block.id, quote=line)
            else:
                columns, header_ref = [], None
            recent.append(line)
            recent = recent[-15:]
            index += 1
    grouped = {}
    for fact in facts:
        key = (
            fact.concept,
            fact.maturity,
            fact.period_start,
            fact.period_end,
            fact.scope,
            fact.basis_date,
            fact.measurement_basis,
        )
        grouped.setdefault(key, []).append(fact)
    accepted = []
    for group in grouped.values():
        if len({f.value for f in group}) != 1:
            rejected.append({"reason": "conflicting_values", "fact_ids": [f.id for f in group]})
        else:
            accepted.append(group[0])
    return accepted, [{"source_id": source.id, **entry} for entry in rejected]
