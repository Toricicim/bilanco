"""Evidence-bound Turkish text extraction, with no discovery or free verdict generation."""

import json
import re

from .ai import AIError
from .assessment import classify
from .documents import normalize
from .equity_models import COMPANIES, Claim, EquitySource, TextExtraction
from .equity_sources import fold
from .equity_tables import NUMBER, parse_turkish
from .models import Block
from .storage import digest, write_json

PROMPT_VERSION = "tr-equity-extraction-2"
CHECKS = (
    "executive_link",
    "transaction",
    "same_parties",
    "financial_effect",
    "business_purpose",
    "controls",
)


def references_valid(refs, blocks):
    return bool(refs) and all(
        r.block_id in blocks
        and len(normalize(r.quote)) >= 12
        and normalize(r.quote) in normalize(blocks[r.block_id].text)
        for r in refs
    )


def validate_relation(claim: Claim, blocks: dict[str, Block], company: str) -> bool:
    draft = claim.relation
    if draft is None:
        return False
    refs = draft.classification_evidence + draft.counter_evidence
    refs += [r for name in CHECKS for r in getattr(draft, name).evidence]
    if not references_valid(refs, blocks) or len(draft.finding_ids) != 1:
        return False
    if draft.finding_ids[0] not in blocks or not draft.company_name:
        return False
    identity = next(
        (c.identity for c in COMPANIES.values() if fold(c.name) == fold(company)), fold(company)
    )
    reporter = fold(draft.company_name)
    alias_quote = " ".join(r.quote for r in refs)
    if reporter == "sirket":
        if identity not in fold(alias_quote) or not re.search(
            r"\([\s\"“”']*Şirket[\s\"“”']*\)", alias_quote, re.I
        ):
            return False
    elif reporter != fold(company):
        if not reporter.startswith(identity):
            return False
        suffix = reporter[len(identity) :].strip()
        if suffix and not set(suffix.replace(".", " ").split()) <= {
            "sanayi",
            "ve",
            "ticaret",
            "anonim",
            "sirketi",
            "a",
            "s",
            "as",
        }:
            return False
    if any(
        getattr(draft, name).answer != "unknown" and not getattr(draft, name).evidence
        for name in CHECKS
    ):
        return False

    def contains(name, evidence):
        return bool(name) and any(
            re.search(r"(?<!\w)" + re.escape(fold(name)) + r"(?!\w)", fold(r.quote))
            for r in evidence
        )

    if any(
        not contains(name, refs)
        for name in (draft.company_name, draft.counterparty, draft.executive)
        if name
    ):
        return False
    if draft.same_parties.answer == "yes" and not (
        contains(draft.company_name, draft.transaction.evidence)
        and contains(draft.counterparty, draft.transaction.evidence)
        and contains(
            draft.counterparty, draft.executive_link.evidence + draft.same_parties.evidence
        )
        and contains(draft.executive, draft.executive_link.evidence)
    ):
        return False
    if draft.transaction.answer == "yes":
        if draft.transaction_scope != "single" or len(draft.transaction.evidence) != 1:
            return False
        quote = fold(draft.transaction.evidence[0].quote)
        if re.search(
            r"gerceklesmedi|gerceklesmemis|yapilmadi|yapilmamis|planlan|ongorul|hen[u]?z|propos|no transaction|not completed",
            quote,
        ):
            return False
        if (
            len(
                re.findall(
                    r"satin aldi|satin almistir|devretti|devretmistir|borc verdi|borc vermistir|odedi|odemistir|\b(?:sold|purchased|transferred|paid|loaned)\b",
                    quote,
                )
            )
            > 1
        ):
            return False
    if draft.executive_link.answer == "yes" and any(
        re.search(r"gorevi bulunmamak|gorev yapmamak|ortagi degil|yoneticisi degil", fold(r.quote))
        for r in draft.executive_link.evidence
    ):
        return False
    if draft.control_basis == "reported_independent":
        quote = fold(" ".join(r.quote for r in draft.controls.evidence))
        if draft.controls.answer != "yes" or not re.search(
            r"bagimsiz|denetim komitesi|independent", quote
        ):
            return False
        if re.search(r"yapilmadi|yapilmamis|bulunmamak|olmaksizin|without|no independent", quote):
            return False
    if draft.controls.answer == "unknown" and draft.control_basis != "not_found":
        return False
    if draft.controls.answer == "yes" and draft.control_basis == "not_found":
        return False
    # Shared priority classifier, while language-specific grounding stays here.
    classify(draft)
    return True


def validate_extraction(
    result: TextExtraction, blocks: list[Block], source: EquitySource, company: str
):
    mapping = {b.id: b for b in blocks}
    claims, forecasts, holdings, rejected = [], [], [], []
    for claim in result.claims:
        ok = references_valid(claim.evidence, mapping)
        if claim.counter_evidence and not references_valid(claim.counter_evidence, mapping):
            ok = False
        quote = fold(" ".join(r.quote for r in claim.evidence))
        if claim.kind == "relation":
            ok = ok and validate_relation(claim, mapping, company)
        elif claim.relation is not None:
            ok = False
        if claim.kind in {"adverse_opinion", "disclaimer", "qualified_opinion", "going_concern"}:
            ok = ok and source.kind in {"financial", "financial_attachment"}
            headings = [fold(line) for r in claim.evidence for line in r.quote.splitlines()]
            expected = {
                "adverse_opinion": ("olumsuz gorus",),
                "disclaimer": ("gorus vermekten kacinma",),
                "qualified_opinion": ("sinirli olumlu gorus", "sartli gorus"),
            }
            if claim.kind in expected:
                ok = ok and any(line in expected[claim.kind] for line in headings)
            else:
                ok = ok and bool(
                    re.search(
                        r"sureklili.{0,120}onemli (?:bir )?belirsizlik|onemli (?:bir )?belirsizlik.{0,120}sureklili",
                        quote,
                    )
                )
                ok = ok and not re.search(
                    r"bulunmamak|mevcut degil|gerektiginde|sorumlu|durumunda", quote
                )
        if claim.kind == "regulatory":
            ok = ok and "islem yasagi" in quote and "karar veril" in quote
        if ok:
            claims.append(claim)
        else:
            rejected.append({"reason": "text_claim_not_grounded", "kind": claim.kind})
    for forecast in result.forecasts:
        text = " ".join(r.quote for r in forecast.evidence)
        ok = references_valid(forecast.evidence, mapping)
        try:
            parse_turkish(forecast.amount_text)
        except ValueError:
            ok = False
        ok = ok and forecast.amount_text in NUMBER.findall(text) and "hasilat" in fold(text)
        ok = ok and bool(re.search(r"tahmin|hedef|ongoru", fold(text)))
        ok = ok and str(forecast.period_end.year) in text
        ok = ok and forecast.period_start.strftime("%d.%m.%Y") in text
        ok = ok and forecast.period_end.strftime("%d.%m.%Y") in text
        ok = ok and source.available_at.date() < forecast.period_end
        ok = ok and forecast.currency == "TRY" and "tl" in fold(text)
        ok = ok and not re.search(r"\bbin\b|\bmilyon\b", fold(text))
        if forecast.basis_date:
            ok = (
                ok
                and forecast.basis_date.strftime("%d.%m.%Y") in text
                and "satin alma gucu" in fold(text)
            )
        if ok:
            forecasts.append(forecast)
        else:
            rejected.append({"reason": "forecast_not_grounded"})
    for holding in result.holdings:
        text = " ".join(r.quote for r in holding.evidence)
        ok = references_valid(holding.evidence, mapping) and holding.holder in text
        ok = ok and holding.effective_date.strftime("%d.%m.%Y") in text
        ok = ok and holding.effective_date <= source.available_at.date()
        ok = ok and holding.percentage_text in re.findall(r"%\s*\d+(?:,\d+)?", text)
        percentage = re.fullmatch(r"%\s*(\d+(?:,\d+)?)", holding.percentage_text)
        ok = ok and percentage is not None
        if percentage:
            ok = ok and 0 <= parse_turkish(percentage[1]) <= 100
        if holding.basis == "capital":
            ok = ok and "sermaye" in fold(text)
        if holding.basis == "voting":
            ok = ok and "oy" in fold(text)
        if ok:
            holdings.append(holding)
        else:
            rejected.append({"reason": "holding_not_grounded"})
    return claims, forecasts, holdings, rejected


def extract_packet(ai, settings, source, blocks, company):
    packet = {
        "prompt_version": PROMPT_VERSION,
        "company": company,
        "as_of": source.available_at.isoformat(),
        "request": (
            "Yalnız verilen Türkçe belgeyi incele. Şirketin sonraki olaylarını veya eğitim bilgini kullanma. "
            "Alıntılı ilişki, denetçi görüşü, süreklilik, tarihli tedbir, faaliyet ve dengeleyici beyan adayları çıkar. "
            "Genel denetçi sorumluluk metni/kilit denetim konusu olumsuz görüş değildir. Risk sınıfı veya tahmin üretme. "
            "relation.finding_ids tek block ID olmalı; her ilişki tek gerçekleşmiş işlem kapsamıyla ayrı olsun. "
            "company_name alıntıda aynen geçen ihraççı adı olmalı; kısa ticari unvan kullanılabilir. "
            "'Şirket' takma adı ancak tam ihraççıyla '(Şirket)' tanımı da alıntıyla kanıtlanıyorsa kullanılabilir. İlişki yoksa relation=null. "
            "forecasts yalnız açık HASILAT tahminleri; tarih/para birimi/satın alma gücü açık değilse uydurma. "
            "amount_text TL tam tutarı kaynakta yazıldığı gibi olmalı; bin/milyon ölçekli tahminleri çıkarma. "
            "holdings yalnız açık sermaye/oy yüzdesi, pay sahibi ve dd.mm.yyyy işlem tarihi içeren alıntılar. "
            "percentage_text '%12,34' biçiminde kaynakta aynen bulunmalı. Eksik bilgi için boş dizi veya unknown kullan. "
            "Tüm iddialar ve karşı açıklamalar verbatim block_id/quote ile dayanaklandırılmalı."
        ),
        "blocks": [b.model_dump(mode="json") for b in blocks],
    }
    key = digest(
        json.dumps([packet, settings.codex_model], ensure_ascii=False, sort_keys=True).encode()
    )
    cache = settings.data_dir / "equity-cache" / "ai" / f"{key}.json"
    cached = False
    if cache.is_file():
        try:
            envelope = json.loads(cache.read_text())
            if (
                envelope["key"] != key
                or digest(json.dumps(envelope["result"], sort_keys=True).encode())
                != envelope["sha256"]
            ):
                raise ValueError("Önbellek özeti eşleşmedi.")
            result = TextExtraction.model_validate(envelope["result"])
            cached = True
        except (ValueError, KeyError):
            raise AIError("AI önbelleği doğrulanamadı.") from None
    else:
        result = ai.ask("tr_equity_evidence_v1", packet, TextExtraction, discovery=False)
        obj = result.model_dump(mode="json")
        write_json(
            cache,
            {"key": key, "result": obj, "sha256": digest(json.dumps(obj, sort_keys=True).encode())},
        )
    return (*validate_extraction(result, blocks, source, company), cached)
