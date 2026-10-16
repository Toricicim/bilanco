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
    "current_assets": ("balance", r"toplam donen varliklar"),
    "current_liabilities": ("balance", r"toplam kisa vadeli yukumlulukler"),
    "total_assets": ("balance", r"toplam varliklar"),
    "total_liabilities": ("balance", r"toplam yukumlulukler"),
    "equity": ("balance", r"toplam ozkaynaklar"),
    "short_debt": ("balance", r"kisa vadeli borclanmalar"),
    "current_long_debt": ("balance", r"uzun vadeli borclanmalarin kisa vadeli kisimlari"),
    "long_debt": ("balance", r"uzun vadeli borclanmalar"),
    "receivables": ("balance", r"ticari alacaklar"),
    "financial_investments": ("balance", r"finansal yatirimlar"),
    "paid_capital": ("balance", r"odenmis sermaye"),
    "revenue": ("income", r"hasilat"),
    "operating_profit": ("income", r"esas faaliyet kari \(?zarari\)?"),
    "net_income": ("income", r"donem kari \(?zarari\)?"),
    "financing_expense": ("income", r"finansman giderleri"),
    "monetary_gain": ("income", r"net parasal pozisyon kazanclari \(?kayiplari\)?"),
    "pretax_profit": ("income", r"surdurulen faaliyetler vergi oncesi kari \(?zarari\)?"),
    "operating_cash_flow": ("cashflow", r"isletme faaliyetlerinden nakit akislari"),
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


def dates_in(text: str) -> list[date]:
    return [datetime.strptime(m, "%d.%m.%Y").date() for m in DATE.findall(text)]


def periods(header: str, flow: bool) -> list[tuple[date | None, date]]:
    # KAP prints all starts in one header row, then all corresponding ends.
    lines = header.splitlines()
    dated = [dates_in(line) for line in lines if dates_in(line)]
    if not dated:
        return []
    ends = dated[-1]
    if not 1 <= len(ends) <= 4:
        return []
    if not flow:
        return [(None, end) for end in ends]
    if len(dated) >= 2 and len(dated[-2]) == len(ends):
        starts = dated[-2]
        if all(
            start.year == end.year and start <= end for start, end in zip(starts, ends, strict=True)
        ):
            return list(zip(starts, ends, strict=True))
    # Some PDF engines put a start/end pair in each column on one line.
    if len(ends) in (4, 8):
        pairs = list(zip(ends[::2], ends[1::2], strict=True))
        if all(a.year == b.year and a <= b for a, b in pairs):
            return pairs
    return []


def extract_financial(
    source: EquitySource, blocks: list[Block]
) -> tuple[list[FinancialFact], list[dict]]:
    if source.kind not in {"financial", "financial_attachment"}:
        return [], []
    text = "\n".join(b.text for b in blocks)
    folded = fold(text)
    scope = (
        "standalone"
        if "konsolide olmayan" in folded
        else ("consolidated" if "konsolide" in folded else None)
    )
    basis_match = re.search(r"(\d{2}\.\d{2}\.20\d{2})\s+donemi\s+finansal rapor", folded)
    if basis_match:
        basis = dates_in(basis_match[0])[0]
    else:
        # Full attachment: explicit purchasing-power date, not a guessed filing date.
        basis_match = re.search(r"(\d{2}\.\d{2}\.20\d{2}).{0,100}satın alma gücü", text, re.I)
        basis = dates_in(basis_match[0])[0] if basis_match else None
    rejected = []
    if not scope or not basis or basis > source.published_at.date():
        return [], [{"source_id": source.id, "reason": "scope_or_basis_unverified"}]
    if not ("tms 29" in folded or "satin alma gucu" in folded):
        return [], [{"source_id": source.id, "reason": "inflation_basis_unverified"}]
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
    recent: list[str] = []
    facts = []
    for block in blocks:
        lines = block.text.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index]
            clean = fold(line)
            if re.fullmatch(r"finansal durum tablosu(?: bilanco)?", clean):
                section = "balance"
            elif clean == "kar veya zarar tablosu":
                section = "income"
            elif re.fullmatch(r"nakit akis tablosu(?: dolayli yontem| dogrudan yontem)?", clean):
                section = "cashflow"
            elif re.fullmatch(r"diger kapsamli gelir tablosu|ozkaynaklar degisim tablosu", clean):
                section = ""
            else:
                # Preserve wrapped labels but never join arbitrary numeric rows.
                if section:
                    for concept, (expected, pattern) in CONCEPTS.items():
                        if section != expected:
                            continue
                        joined = line
                        match = None
                        for width in (1, 2, 3):
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
                        start = re.search(r"\(?-?\d|[—–-](?=\s|$)", joined)
                        if not start:
                            continue
                        tail = joined[start.start() :].strip()
                        values = NUMBER.findall(tail)
                        residue = NUMBER.sub("", tail).strip(" \t|:")
                        if (
                            len(values) == len(columns) + 1
                            and len(values[0]) <= 2
                            and "dipnot" in fold(" ".join(recent))
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
                                        f"{source.id}:{concept}:{begin}:{end}:{value}".encode()
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
        key = fact.concept, fact.period_start, fact.period_end, fact.scope, fact.basis_date
        grouped.setdefault(key, []).append(fact)
    accepted = []
    for group in grouped.values():
        if len({f.value for f in group}) != 1:
            rejected.append({"reason": "conflicting_values", "fact_ids": [f.id for f in group]})
        else:
            accepted.append(group[0])
    return accepted, rejected
