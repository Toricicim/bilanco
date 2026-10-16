"""Location-preserving readers and conservative, non-LLM financial table extraction."""

import io
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import pdfplumber
from bs4 import BeautifulSoup

from .acquisition import decode_text
from .models import Block, Fact, Locator, Source
from .storage import digest

CONCEPTS = {
    "current_assets": r"total current assets",
    "current_liabilities": r"total current liabilities",
    "total_assets": r"total assets",
    "total_liabilities": r"total liabilities",
    "equity": r"(?:total )?(?:shareholders'?|stockholders'?) equity",
    "cash": r"cash and cash equivalents",
    "long_term_debt": r"long[- ]term debt(?:, net)?",
    "short_term_debt": r"short[- ]term debt",
    "net_income": r"net (?:income|earnings)(?: \(loss\))?",
    "operating_cash_flow": (
        r"(?:net )?cash (?:provided by|provided from|used in|from) operating activities"
    ),
}
HEADINGS = {
    "balance": r"consolidated balance sheets?",
    "income": r"consolidated (?:statements? of (?:income|operations|earnings)|income statements?)",
    "cashflow": r"consolidated statements? of cash flows?",
}
BALANCE_CONCEPTS = set(CONCEPTS) - {"net_income", "operating_cash_flow"}
AMOUNT = re.compile(r"\(?-?\$?\s*\d[\d,]*(?:\.\d+)?\)?|--?|—")
YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")


def normalize(text: str) -> str:
    return " ".join(text.split())


def read_document(source: Source, content: bytes) -> tuple[list[Block], list[str]]:
    """No network, model, OCR download or model-generated text in this reader."""
    sections: list[tuple[int | None, str]] = []
    issues: list[str] = []
    if content.startswith(b"%PDF-"):
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                if len(pdf.pages) > 150:
                    return [], ["Belge 150 sayfa sınırını aşıyor."]
                for index, page in enumerate(pdf.pages, 1):
                    text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                    if len(text.strip()) < 20:
                        issues.append(f"Sayfa {index}: metin okunamadı; OCR bu sürümde yok.")
                    sections.append((index, text))
        except Exception as exc:
            return [], [f"PDF okunamadı ({type(exc).__name__})."]
    else:
        text = decode_text(content)
        # A submission can also contain exhibits and another company's reports.
        # Read only the primary document, with the already validated form type.
        if "<DOCUMENT>" in text.upper():
            matches = re.findall(r"<DOCUMENT>(.*?)</DOCUMENT>", text, re.I | re.S)
            primary = [
                part
                for part in matches
                if re.search(r"<TYPE>\s*(?:10-K|10-Q|8-K)\s*(?:\r?\n|<)", part, re.I)
            ]
            if not primary:
                return [], ["SEC dosyasında özgün ana belge bulunamadı."]
            text = primary[0]
            match = re.search(r"<TEXT>(.*?)(?:</TEXT>|$)", text, re.I | re.S)
            text = match[1] if match else text
        if re.search(r"<(?:html|table|pre|p|div)\b", text, re.I):
            soup = BeautifulSoup(text, "html.parser")
            for node in soup(["script", "style"]):
                node.decompose()
            # Preserve the year/column relationship in HTML tables.
            for table in list(soup.find_all("table")):
                if not table.find("tr"):
                    # Legacy EDGAR TABLE/CAPTION/S/C tags enclose aligned text,
                    # not HTML rows. Keep its original line breaks and spacing.
                    table.replace_with("\n" + table.get_text() + "\n")
                    continue
                rows = []
                for row in table.find_all("tr"):
                    cells = [
                        normalize(cell.get_text(" ", strip=True))
                        for cell in row.find_all(["td", "th"])
                    ]
                    rows.append("   ".join(cells))
                table.replace_with("\n" + "\n".join(rows) + "\n")
            text = soup.get_text("\n")
        sections.append((None, text))
    blocks = []
    for page, text in sections:
        lines = text.splitlines()
        # Stable locators refer to the original extracted page/line interval.
        for start in range(0, len(lines), 65):
            part = "\n".join(lines[start : start + 65])
            if not part.strip():
                continue
            block_id = digest(f"{source.id}:{page}:{start + 1}:{part}".encode())[:24]
            blocks.append(
                Block(id=block_id, source_id=source.id, page=page, line_start=start + 1, text=part)
            )
    if not blocks:
        issues.append("Belgeden kullanılabilir metin çıkarılamadı.")
    return blocks, issues


def archive_identity_ok(blocks: list[Block]) -> bool:
    """Identity checks are not proof of byte equivalence or an independent audit."""
    text = normalize(" ".join(block.text for block in blocks)).lower()
    return (
        bool(re.search(r"\benron\b", text))
        and bool(re.search(r"1999.{0,60}annual report|annual report.{0,60}1999", text))
        and "consolidated" in text
        and not re.search(r"form 10-k/a|\brestat(?:ed|ement)\b|\bamended\b", text)
    )


def parse_amount(raw: str) -> Decimal:
    value = raw.strip().replace("$", "").replace(" ", "")
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]
    if not re.fullmatch(r"-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", value):
        # A dash is not silently reinterpreted as a printed zero.
        raise InvalidOperation
    result = Decimal(value.replace(",", ""))
    if not result.is_finite():
        raise InvalidOperation
    return result


def logical_rows(text: str):
    """Join only recognized financial labels wrapped before their amounts."""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not re.search(r"\d", line):
            for width in (2, 3):
                span = lines[index : index + width]
                if len(span) != width:
                    continue
                joined = normalize(" ".join(span)).lower()
                if any(
                    re.fullmatch(rf"(?:{pattern})\s+[$(\d\-—][\d\s,$().\-—]*", joined)
                    for pattern in CONCEPTS.values()
                ):
                    line = "\n".join(span)
                    index += width - 1
                    break
        yield line
        index += 1


def extract_facts(blocks: list[Block], as_of: date) -> tuple[list[Fact], list[dict]]:
    facts: list[Fact] = []
    rejected: list[dict] = []
    section = ""
    years: list[int] = []
    header: Locator | None = None
    unit: Locator | None = None
    scale = 1
    currency = "unknown"
    currency_evidence: Locator | None = None
    source_id = None
    for block in blocks:
        if block.source_id != source_id:
            section, years, header, unit, currency = "", [], None, None, "unknown"
            currency_evidence = None
            source_id = block.source_id
        for line in logical_rows(block.text):
            clean = normalize(line).replace("’", "'")
            lower = clean.lower()
            if re.match(r"consolidated (?:statements?|balance|income)", lower):
                section = ""
            for name, pattern in HEADINGS.items():
                if re.fullmatch(pattern, lower):
                    section, years, header, unit, currency = name, [], None, None, "unknown"
                    currency_evidence = None
            if re.match(r"(?:\d+\.? )?notes to (?:the )?consolidated", lower):
                section = ""
            if not section:
                continue
            if re.search(r"\bin (?:millions|thousands)\b", lower):
                scale = 1_000_000 if "millions" in lower else 1000
                unit = Locator(block_id=block.id, quote=line)
                if "dollar" in lower or "$" in clean:
                    currency = "dollars"
                    currency_evidence = Locator(block_id=block.id, quote=line)
            # Dollar symbols elsewhere on the same financial table are explicit
            # currency context, not an inferred ISO currency code.
            if "$" in clean:
                currency = "dollars"
                currency_evidence = Locator(block_id=block.id, quote=line)
            found_years = [int(value) for value in YEAR.findall(clean)]
            if 2 <= len(found_years) <= 3 and len(set(found_years)) == len(found_years):
                remainder = YEAR.sub("", clean)
                remainder = re.sub(
                    r"\(in (?:millions|thousands)(?: of dollars)?(?:, except (?:per share amounts|(?:number of )?shares))?\)",
                    "",
                    remainder,
                    flags=re.I,
                )
                remainder = re.sub(
                    r"\b(?:years?|ended|december|dec|as|of|at)\b", "", remainder, flags=re.I
                )
                if not re.search(r"[A-Za-z]", remainder):
                    years = found_years
                    header = Locator(block_id=block.id, quote=line)
                    continue
            if not years or header is None or unit is None:
                continue
            for concept, pattern in CONCEPTS.items():
                if section == "balance" and concept not in BALANCE_CONCEPTS:
                    continue
                if section != "balance" and concept in BALANCE_CONCEPTS:
                    continue
                if concept == "operating_cash_flow" and section != "cashflow":
                    continue
                match = re.match(rf"^(?:{pattern})(?=\s|\.|:|$)", lower)
                if not match:
                    continue
                tail = clean[match.end() :].strip(" .:|")
                if not tail:
                    continue  # A subsection label or prose continuation is not a numeric row.
                amounts = AMOUNT.findall(tail)
                residue = AMOUNT.sub("", tail).strip(" .:|\t")
                if re.search(r"[A-Za-z]", residue):
                    # A longer label (e.g. net income before tax) is a different
                    # concept, not a malformed row for the requested concept.
                    continue
                if residue or len(amounts) != len(years):
                    rejected.append(
                        {
                            "reason": "ambiguous_table_columns",
                            "concept": concept,
                            "block_id": block.id,
                            "row": line,
                        }
                    )
                    continue
                for year, amount in zip(years, amounts, strict=True):
                    if year > as_of.year:
                        continue
                    try:
                        value = parse_amount(amount)
                    except InvalidOperation:
                        rejected.append(
                            {
                                "reason": "amount_missing_or_invalid",
                                "concept": concept,
                                "period": year,
                                "block_id": block.id,
                                "row": line,
                            }
                        )
                        continue
                    if concept == "operating_cash_flow" and "used in" in lower and value > 0:
                        # Positive magnitude + outflow label: sign is not established.
                        # Never turn this into positive cash generation or invent a sign.
                        rejected.append(
                            {
                                "reason": "cash_flow_sign_ambiguous",
                                "concept": concept,
                                "period": year,
                                "block_id": block.id,
                                "row": line,
                            }
                        )
                        continue
                    fact_id = digest(f"{concept}:{year}:{value}:{block.id}:{line}".encode())[:24]
                    facts.append(
                        Fact(
                            id=fact_id,
                            concept=concept,
                            period=year,
                            value=value,
                            unit=currency,
                            scale=scale,
                            evidence=Locator(block_id=block.id, quote=line),
                            header_evidence=header,
                            unit_evidence=unit,
                        )
                    )
                    facts[-1].currency_evidence = currency_evidence
                break
    # A conflicting value is not arbitrarily resolved by first/last row wins.
    grouped: dict[tuple[str, int], list[Fact]] = {}
    for fact in facts:
        grouped.setdefault((fact.concept, fact.period), []).append(fact)
    accepted = []
    for (concept, period), group in grouped.items():
        variants = {(f.value * f.scale, f.unit) for f in group}
        if len(variants) != 1:
            rejected.append(
                {
                    "reason": "conflicting_values",
                    "concept": concept,
                    "period": period,
                    "fact_ids": [f.id for f in group],
                }
            )
        else:
            accepted.append(group[0])
    return accepted, rejected
