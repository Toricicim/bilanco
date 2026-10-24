"""Evidence-bound Turkish text extraction, with no discovery or free verdict generation."""

import json
import re

from .ai import AIError
from .assessment import REQUEST as RELATION_REQUEST
from .assessment import classify
from .documents import normalize
from .equity_document_facts import document_fact_error
from .equity_models import COMPANIES, Claim, EquitySource, TextExtraction
from .equity_signals import CATALOG, signal_error
from .equity_sources import fold
from .equity_tables import NUMBER, dates_in, parse_turkish
from .models import Block
from .storage import digest, write_json

PROMPT_VERSION = "tr-equity-extraction-5"
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


def contains_name(name, refs):
    return bool(name) and any(
        re.search(r"(?<!\w)" + re.escape(fold(name)) + r"(?!\w)", fold(r.quote)) for r in refs
    )


def issuer_valid(name, refs, company):
    identity = next(
        (c.identity for c in COMPANIES.values() if fold(c.name) == fold(company)), fold(company)
    )
    reporter = fold(name)
    alias_quote = " ".join(r.quote for r in refs)
    if reporter == "sirket":
        return contains_name(identity, refs) and bool(
            re.search(r"\([\s\"“”']*Şirket[\s\"“”']*\)", alias_quote, re.I)
        )
    if reporter != fold(company):
        if not reporter.startswith(identity):
            return False
        suffix = reporter[len(identity) :].strip()
        if suffix and not set(suffix.replace(".", " ").split()) <= {
            "sanayi",
            "san",
            "ve",
            "ticaret",
            "tic",
            "anonim",
            "sirketi",
            "a",
            "s",
            "as",
        }:
            return False
    return contains_name(name, refs)


def relation_error(claim: Claim, blocks: dict[str, Block], company: str) -> str | None:
    draft = claim.relation
    if draft is None:
        return "relation_missing"
    refs = draft.classification_evidence + draft.counter_evidence
    refs += [r for name in CHECKS for r in getattr(draft, name).evidence]
    if not references_valid(refs, blocks) or len(draft.finding_ids) != 1:
        return "relation_references_invalid"
    if draft.finding_ids[0] not in blocks or not issuer_valid(draft.company_name, refs, company):
        return "issuer_identity_not_grounded"
    if any(
        getattr(draft, name).answer != "unknown" and not getattr(draft, name).evidence
        for name in CHECKS
    ):
        return "atomic_answer_without_evidence"

    contains = contains_name
    unknown_names = {"", "unknown", "bilinmiyor", "null"}
    executive = "" if fold(draft.executive) in unknown_names else draft.executive
    if not contains(draft.counterparty, refs):
        return "counterparty_not_grounded"
    if executive and not contains(executive, refs):
        return "executive_not_grounded"
    if not executive and (
        draft.executive_link.answer == "yes" or draft.same_parties.answer == "yes"
    ):
        return "executive_chain_incomplete"
    if draft.same_parties.answer == "yes" and not (
        contains(draft.company_name, draft.transaction.evidence)
        and contains(draft.counterparty, draft.transaction.evidence)
        and contains(
            draft.counterparty, draft.executive_link.evidence + draft.same_parties.evidence
        )
        and contains(draft.executive, draft.executive_link.evidence)
    ):
        return "same_parties_not_grounded"
    if draft.transaction.answer == "yes":
        if draft.transaction_scope != "single" or len(draft.transaction.evidence) != 1:
            return "transaction_scope_not_single"
        quote = fold(draft.transaction.evidence[0].quote)
        if re.search(
            r"gerceklesmedi|gerceklesmemis|yapilmadi|yapilmamis|planlan|ongorul|hen[u]?z|propos|no transaction|not completed",
            quote,
        ):
            return "transaction_negated_or_proposed"
        if (
            len(
                re.findall(
                    r"satin aldi|satin almistir|devretti|devretmistir|borc verdi|borc vermistir|odedi|odemistir|\b(?:sold|purchased|transferred|paid|loaned)\b",
                    quote,
                )
            )
            > 1
        ):
            return "multiple_transactions_pooled"
    if draft.executive_link.answer == "yes" and any(
        re.search(r"gorevi bulunmamak|gorev yapmamak|ortagi degil|yoneticisi degil", fold(r.quote))
        for r in draft.executive_link.evidence
    ):
        return "executive_link_negated"
    if draft.control_basis == "reported_independent":
        quote = fold(" ".join(r.quote for r in draft.controls.evidence))
        if draft.controls.answer != "yes" or not re.search(
            r"bagimsiz|denetim komitesi|independent", quote
        ):
            return "independent_control_not_grounded"
        if re.search(r"yapilmadi|yapilmamis|bulunmamak|olmaksizin|without|no independent", quote):
            return "independent_control_negated"
    if draft.controls.answer == "unknown" and draft.control_basis != "not_found":
        return "unknown_control_basis_conflict"
    if draft.controls.answer == "yes" and draft.control_basis == "not_found":
        return "control_basis_missing"
    # Shared priority classifier, while language-specific grounding stays here.
    classify(draft)
    return None


def validate_relation(claim: Claim, blocks: dict[str, Block], company: str) -> bool:
    return relation_error(claim, blocks, company) is None


def observation_error(obj, mapping, source, company):
    refs = (
        obj.evidence + obj.counter_evidence + obj.controls.evidence + obj.business_purpose.evidence
    )
    if obj.amount_evidence:
        refs += [obj.amount_evidence]
    if not references_valid(refs, mapping):
        return "observation_references_invalid"
    if not issuer_valid(obj.company_name, refs, company):
        return "observation_issuer_not_grounded"
    if not contains_name(obj.counterparty, obj.evidence):
        return "observation_counterparty_not_grounded"
    if obj.person and not contains_name(obj.person, obj.evidence):
        return "observation_person_not_grounded"
    text = fold(" ".join(r.quote for r in obj.evidence))
    patterns = {
        "executive_role": r"yonetim|yonetici|mudur|baskan|gorev",
        "ownership": r"pay|ortak|sermaye",
        "related_purchase": r"alis|satin al",
        "related_sale": r"satis|satil|satmistir",
        "guarantee": r"teminat|\btri\b|kefalet|ipotek|rehin",
        "asset_transaction": r"satin al|satil|kirala|devred|devret",
        "treasury_investment": r"yatirim fon|finansal yatirim|menkul kiymet",
    }
    if not re.search(patterns[obj.kind], text):
        return "observation_kind_not_grounded"
    if obj.kind.startswith("related_") and not re.search(r"iliskili|ana ortak", text):
        return "related_status_not_grounded"
    if obj.kind == "executive_role" and not obj.person:
        return "observation_person_missing"
    for field in (obj.period_end, obj.effective_date, obj.basis_date):
        if field and (
            field > source.available_at.date()
            or not any(field in dates_in(r.quote) for r in obj.evidence)
        ):
            return "observation_date_not_grounded"
    if obj.basis_date and not any(
        "satin alma gucu" in fold(r.quote) and obj.basis_date in dates_in(r.quote)
        for r in obj.evidence
    ):
        return "observation_basis_not_grounded"
    if obj.amount_text is not None:
        if not obj.amount_evidence or obj.currency is None:
            return "observation_amount_context_missing"
        try:
            parse_turkish(obj.amount_text)
        except ValueError:
            return "observation_amount_invalid"
        if obj.amount_text not in NUMBER.findall(obj.amount_evidence.quote):
            return "observation_amount_not_grounded"
        units = {"TRY": r"\btl\b|turk lirasi", "USD": r"\busd\b|dolar", "EUR": r"\beur\b|avro|euro"}
        if not re.search(units[obj.currency], text) or re.search(
            r"\bbin\b|\bmilyon\b|\bmilyar\b", fold(obj.amount_evidence.quote)
        ):
            return "observation_currency_or_scale_unverified"
    elif obj.amount_evidence or obj.currency:
        return "observation_amount_missing"
    for check in (obj.controls, obj.business_purpose):
        if check.answer != "unknown" and not check.evidence:
            return "observation_atomic_evidence_missing"
    control_text = fold(" ".join(r.quote for r in obj.controls.evidence))
    if obj.controls.answer == "yes" and not re.search(
        r"onay|degerleme|komite|oy|bagimsiz", control_text
    ):
        return "observation_controls_not_grounded"
    absent_control = re.search(
        r"onay (?:alinmadi|alinmamis|verilmedi|verilmemis)|onaysiz|"
        r"degerleme (?:yapilmadi|yapilmamis)|onay(?:i)? olmadan",
        control_text,
    )
    if obj.controls.answer == "no" and not absent_control:
        return "observation_control_absence_not_explicit"
    if obj.controls.answer == "no" and re.search(
        r"iddia|dogru degil|soz konusu degil|varsay", control_text
    ):
        return "observation_control_absence_contested"
    if obj.controls.answer == "yes" and absent_control:
        return "observation_controls_negated"
    if obj.controls.answer == "no" and not contains_name(obj.counterparty, obj.controls.evidence):
        return "observation_controls_other_party"
    if obj.controls.answer == "conflicting" and len(obj.controls.evidence) < 2:
        return "observation_control_conflict_incomplete"
    return None


def validate_extraction(
    result: TextExtraction,
    blocks: list[Block],
    source: EquitySource,
    company: str,
    *,
    include_observations=False,
    include_signals=False,
    include_document_facts=False,
):
    mapping = {b.id: b for b in blocks}
    claims, forecasts, holdings, rejected = [], [], [], []
    for claim in result.claims:
        error = None
        ok = references_valid(claim.evidence, mapping)
        if claim.counter_evidence and not references_valid(claim.counter_evidence, mapping):
            ok = False
        quote = fold(" ".join(r.quote for r in claim.evidence))
        if claim.kind == "relation":
            error = relation_error(claim, mapping, company)
            ok = ok and error is None
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
            if claim.relation and fold(claim.relation.executive) in {
                "unknown",
                "bilinmiyor",
                "null",
            }:
                claim = claim.model_copy(
                    update={"relation": claim.relation.model_copy(update={"executive": ""})}
                )
            claims.append(claim)
        else:
            rejected.append(
                {
                    "reason": "text_claim_not_grounded",
                    "detail": error or "claim_references_or_kind_invalid",
                    "kind": claim.kind,
                    "source_id": source.id,
                    "candidate": claim.model_dump(mode="json"),
                }
            )
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
            rejected.append(
                {
                    "reason": "forecast_not_grounded",
                    "source_id": source.id,
                    "candidate": forecast.model_dump(mode="json"),
                }
            )
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
            rejected.append(
                {
                    "reason": "holding_not_grounded",
                    "source_id": source.id,
                    "candidate": holding.model_dump(mode="json"),
                }
            )
    observations = []
    for obj in result.observations:
        error = observation_error(obj, mapping, source, company)
        if error:
            rejected.append(
                {
                    "reason": error,
                    "source_id": source.id,
                    "kind": obj.kind,
                    "candidate": obj.model_dump(mode="json"),
                }
            )
        else:
            observations.append(obj)
    signals = []
    for obj in result.signals:
        error = signal_error(
            obj,
            mapping,
            source,
            company,
            issuer_valid=issuer_valid,
            references_valid=references_valid,
            dates_in=dates_in,
        )
        if error:
            rejected.append(
                {
                    "reason": error,
                    "source_id": source.id,
                    "kind": obj.kind,
                    "candidate": obj.model_dump(mode="json"),
                }
            )
        else:
            signals.append(obj)
    document_facts = []
    for obj in result.document_facts:
        error = document_fact_error(
            obj,
            mapping,
            source,
            company,
            references_valid=references_valid,
            issuer_valid=issuer_valid,
            contains_name=contains_name,
        )
        if error:
            rejected.append(
                {
                    "reason": error,
                    "source_id": source.id,
                    "kind": obj.kind,
                    "candidate": obj.model_dump(mode="json"),
                }
            )
        else:
            document_facts.append(obj)
    if source.role == "related_fund":
        if claims or forecasts or holdings or observations or signals:
            rejected.append({"reason": "related_fund_not_issuer_evidence", "source_id": source.id})
        claims, forecasts, holdings, observations, signals = [], [], [], [], []
    output = (claims, forecasts, holdings, rejected)
    if include_observations:
        output = (*output, observations)
    if include_signals:
        output = (*output, signals)
    return (*output, document_facts) if include_document_facts else output


def extract_packet(
    ai,
    settings,
    source,
    blocks,
    company,
    *,
    allow_legacy_cache=False,
    record=None,
    retry_cached=False,
):
    packet = {
        "prompt_version": PROMPT_VERSION,
        "company": company,
        "schema_sha256": digest(
            json.dumps(TextExtraction.model_json_schema(), sort_keys=True).encode()
        ),
        "relation_contract": RELATION_REQUEST,
        "investor_checks": {
            k: {"title": v.title, "required_context": v.missing} for k, v in CATALOG.items()
        },
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
            "İsmi bilinmeyen executive için boş string kullan; unknown gerçek kişi adı değildir. "
            "observations: yönetici rolü, sahiplik, ilişkili alış/satış toplamı, teminat, varlık işlemi ve "
            "hazine yatırımlarını yönetici adı veya tek işlem şartı aramadan ayrı kaynak olguları olarak çıkar. "
            "kind=executive_role yalnız rol, related_purchase/related_sale dönem toplamı; asset_transaction tekil varlık olayıdır. "
            "Bunlar risk veya hile hükmü değildir. Birbirinden farklı şirket/işlem/tarihler için kontrol beyanlarını birleştirme. "
            "Şirket/karşı taraf/kişi isimleri ve amount_text aynen alıntıdan kopyalanmalı; bilinmeyen kişi/tarih/tutar null. "
            "amount_evidence tutarın bulunduğu etiketli satır; evidence ilgili tablo başlığı/dönem/para birimini de içersin. "
            "Bin/milyon ölçekli tutarı observations'a çıkarma; kur/ölçek/tarih hesaplama. "
            "Kontrol ve ticari amaç bulunamazsa unknown; açık yokluk beyanı olmadan no kullanma. "
            "Değerleme, onay, ödeme, tescil gibi dengeleyici açıklamaları aynı işlemin counter_evidence alanında koru. "
            "signals: investor_checks başlıkları için yalnız belgede açıkça ifade edilen belirli olgu/beyanları çıkar. "
            "assertion=issue kaynağın açık sorun beyanıdır; senin risk yorumun değildir. counterstatement normal açıklama veya sorunu reddeden beyandır. "
            "Genel risk politikası, gelecekte olabilecek risk ve belge bulunamaması issue değildir. Emin değilsen unknown veya boş dizi. "
            "subject, company_name, event_date ve period_end yalnız alıntıdan; olay/karşı taraf/dönemleri birleştirme. "
            "Sonraki hukuk/düzenleyici tespiti issuer_statement diye verme; regulatory_action/court_decision/allegation olarak ayır. "
            "Dava açılması mahkumiyet, mahkumiyet kesinleşme değildir. Birbirinden ayrı yargılama ve tarihleri birleştirme. "
            "Net ortak satışı ile olumlu anlatı aynı tarih aralığında ikisi de kanıtlı değilse insider_sales issue verme; tipe dönüşüm/virman satış değildir. "
            "Günlük fiyattan emir iptali, kapanış manipülasyonu veya nihai tek kişi çıkarma. "
            "TMS29 kazancı, ilişkili işlem, geçici fon yatırımı ve tek negatif nakit tek başına usulsüzlük değildir. "
            "Nakit akışındaki yatırım düzeltmesini, tahsilat/ödeme ve proje takvimini karşı açıklamalarda koru. "
            "Oran/gerçekleşme/ekonomik zarar hesaplama; sayıları ve ifadeleri kopyala, hesap Python'da yapılır. "
            "document_facts: risk yorumu olmadan nötr olguları çıkar: fund_position (şirketin fon yatırımı), "
            "fund_net_assets (fon toplam değeri), fund_redemption_days (iade günü), proceeds_plan, proceeds_spent "
            "(aynı projenin planlanan/gerçekleşen fon kullanımı), contract_owner (sözleşmenin tarafı). "
            "entity_name raporu yayımlayan tüzel kişi, subject kaynakta aynen geçen fon KODU/proje/sözleşme adı. "
            "value_text yalnız kaynakta basılan tam tutar, value_evidence ilgili etiketli satır; evidence dönem, birim ve kapsam başlıklarını da içersin. "
            "Bin/milyon/milyar veya yüzde satırlarını bu alana çıkarma; ölçek dönüştürme. "
            "period_start/end, effective_date ve basis_date yalnız belgede açık tarih varsa doldur; diğerleri null. "
            "İlk plan ile gerçekleşme/sonradan değiştirilmiş planı birbirine karıştırma. "
            "contract_owner için counterparty açıkça sözleşmenin tarafı olan tüzel kişinin tam adıdır; grup ortaklığı gelir atfı değildir. "
            "scope ve measurement_basis açık değilse unknown; nominal veya solo varsayma. "
            "Fon belgesinde yalnız fonun kendi toplam değeri ve iade şartlarını çıkar; onu analiz edilen şirketin geliri/ilişkisi gibi sunma. "
            "fund_redemption_days için day_basis yalnız açık 'iş günü' varsa business, 'takvim günü' varsa calendar; diğer durumda unknown. "
            "Fon alımı ile fonun şirket hissesi alımı ters yönlerdir; fund_position yalnız şirketin elindeki fon pozisyonudur. "
            "Kaynağın 'sorun var' demesi nötr olgu için şart değildir; farkı veya oranı sen hesaplama. "
            "Tüm iddialar ve karşı açıklamalar verbatim block_id/quote ile dayanaklandırılmalı."
        ),
        "blocks": [b.model_dump(mode="json") for b in blocks],
    }
    record = record if record is not None else {}

    def cache_path(model):
        key = digest(json.dumps([packet, model], ensure_ascii=False, sort_keys=True).encode())
        return key, settings.data_dir / "equity-cache" / "ai" / f"{key}.json"

    key, cache = cache_path(settings.codex_model)
    paths = [(key, cache, settings.codex_model)]
    if allow_legacy_cache and settings.codex_model:
        legacy_key, legacy_path = cache_path("")
        paths.append((legacy_key, legacy_path, "legacy_cli_default"))
    cached = False
    for expected, path, model in paths:
        if not path.is_file():
            continue
        try:
            envelope = json.loads(path.read_text())
            if (
                envelope["key"] != expected
                or digest(json.dumps(envelope["result"], sort_keys=True).encode())
                != envelope["sha256"]
            ):
                raise ValueError("Önbellek özeti eşleşmedi.")
            result = TextExtraction.model_validate(envelope["result"])
            cached = True
            record.update(model=envelope.get("model", model), cache_key=expected)
            break
        except (ValueError, KeyError):
            raise AIError("AI önbelleği doğrulanamadı.") from None
    else:
        result = ai.ask("tr_equity_evidence_v2", packet, TextExtraction, discovery=False)
        record["model"] = getattr(ai, "last_model", settings.codex_model)

    def validate(candidate):
        return validate_extraction(
            candidate,
            blocks,
            source,
            company,
            include_observations=True,
            include_signals=True,
            include_document_facts=True,
        )

    validated = validate(result)
    # Index 3 is the rejected candidate list; validation does not label fraud.
    if cached and validated[3] and not retry_cached:
        record["cached_rejections_retained"] = len(validated[3])
    if validated[3] and hasattr(ai, "escalate") and (not cached or retry_cached):
        record["primary_validation_rejections"] = validated[3]
        try:
            stronger = ai.escalate(
                "tr_equity_evidence_v2", packet, TextExtraction, from_model=record.get("model")
            )
            if stronger is not None:
                stronger_validated = validate(stronger)
                record["fallback_model"] = ai.last_model
                record["fallback_rejections"] = stronger_validated[3]
                # Keep the route with fewer mechanically invalid candidates. This
                # is not a measure of semantic completeness or fraud detection.
                if len(stronger_validated[3]) <= len(validated[3]):
                    result, validated = stronger, stronger_validated
                    cached = False
                    record["model"] = ai.last_model
                    record["fallback_selected"] = True
        except AIError as exc:
            record["fallback_error"] = str(exc)
    if not cached:
        obj = result.model_dump(mode="json")
        write_json(
            cache,
            {
                "key": key,
                "result": obj,
                "sha256": digest(json.dumps(obj, sort_keys=True).encode()),
                "model": record.get("model"),
            },
        )
    return (*validated, cached)
