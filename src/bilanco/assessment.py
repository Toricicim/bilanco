"""A bounded, offline-source assessment stage. No acquisition or web discovery here."""

import json
import re
import time
import uuid
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from html import escape

from .ai import AIError, Codex
from .assessment_models import Assessment, RelationDraft, RelationReview, ReviewCase
from .config import Settings
from .documents import normalize
from .models import Analysis, Locator
from .report import literal
from .storage import Store, analysis_digest, atomic_write, digest, write_json

FOCUS = {"related_party", "executive_conflict"}
CHECKS = (
    "executive_link",
    "transaction",
    "same_parties",
    "financial_effect",
    "business_purpose",
    "controls",
)
CHECK_LABELS = {
    "executive_link": "Yöneticinin karşı taraftaki yönetim/kontrol bağlantısı",
    "transaction": "Şirket ve karşı taraf arasındaki işlem",
    "same_parties": "Bağlantı ve işlemin aynı taraflara ait olması",
    "financial_effect": "Açıklanan finansal etki",
    "business_purpose": "İşlemin açıklanan ticari amacı",
    "controls": "Açıklanan kontrol mekanizmaları",
}
PRIORITY_LABELS = {
    "first_review": "Öncelikli inceleme",
    "further_review": "Ek inceleme",
    "context": "Bağlamsal bilgi",
    "unassessed": "Değerlendirilemedi",
}
ANSWER_LABELS = {
    "yes": "Belgede destek var",
    "no": "Belgede açık olumsuz ifade var",
    "unknown": "Bilinmiyor",
    "conflicting": "Çelişkili",
}
REQUEST = """Assess ONLY these finding IDs against the supplied source blocks. Return cases,
covering every supplied finding ID exactly once. Combine findings only when they describe the
same relationship/transaction. Do not rank risk, predict fraud, use later events, or invent names,
amounts, dates, independent checks, or aliases. No external search.
For each case answer these atomic questions with yes/no/unknown/conflicting and VERBATIM quotes:
executive_link: does an officer of the reporting company have an executive, controlling,
managing-member or general-partner management role on the counterparty side? An employment
agreement WITH the reporting company, passive ownership, or merely mentioning an officer is NOT
this link. A role at the counterparty's general partner qualifies only if explicitly connected.
transaction: is there an actual transaction between the reporting company and this counterparty?
same_parties: do the executive link and transaction refer to the same company/counterparty?
Different names are not aliases. Fund A and Fund A2, for example, must NEVER be equated by substring;
a shared general partner, if explicitly stated, is a relationship, NOT identity.
financial_effect: is an impact on income, cash, assets or liabilities explicitly described?
business_purpose: is the business purpose OF THIS TRANSACTION described (not a generic company description)?
controls: are approval, valuation, voting, economic-interest restrictions or other controls described?
For controls distinguish management_assertion from reported_independent. Reporting a control is
not proof it operated. An arm's-length assertion, clean audit opinion or 'fair value' alone is
NOT independent verification of this transaction. Missing disclosure means unknown, never no.
Every yes/no/conflicting answer needs a source quote; unknown may have empty evidence.
kind is employment for routine employment/consulting/compensation exhibits, ownership for
ownership alone, related_transaction for a related transaction, executive_relationship for
role alone, or unresolved. Copy a classification passage in classification_evidence EVEN IF
all six atomic checks are unknown (e.g. a passive ownership disclosure). This passage also
grounds the names you return. Preserve explicit negation and all relevant counterstatements in
counter_evidence. company_name, counterparty and executive must be verbatim source strings;
an anonymous officer stays anonymous. Empty names if unknown. Do not infer a name from memory.
Each case must contain evidence overlapping the original quotes of its finding IDs.
"""
BOUNDARIES = [
    "Öncelik bir inceleme önerisidir; risk olasılığı veya şirketin risk sınıfı değildir.",
    "Alıntı eşleşmesi kodla kontrol edildi; modelin anlam yorumu bağımsız doğrulanmış sayılmaz.",
    "İnsan etiketli iki değerlendiricili kalibrasyon henüz tamamlanmadı.",
    "Bu aşama yalnız yönetici/ilişkili işlem adaylarını derinleştirir; diğer AI türleri kapsam dışında korunur.",
    "Açıklama bulunamaması kontrolün olmadığı veya işlemin normal olduğu anlamına gelmez.",
    "Modelin geçmiş bilgisi silinemez; tamamen kör bir tarihsel tahmin deneyi değildir.",
]


def _unique(refs: list[Locator]) -> list[Locator]:
    return list({(r.block_id, normalize(r.quote)): r for r in refs}.values())


def _references(draft: RelationDraft) -> list[Locator]:
    return _unique(
        draft.classification_evidence
        + [r for name in CHECKS for r in getattr(draft, name).evidence]
        + draft.counter_evidence
    )


def make_packages(analysis: Analysis, max_chars: int) -> tuple[list[dict], list[str]]:
    """Each candidate occurs once; context blocks are shared within each package."""
    blocks = analysis.blocks
    positions = {b.id: i for i, b in enumerate(blocks)}
    sources = {s.id: s for s in analysis.sources}
    groups: dict[str, list] = {}
    omitted = []
    for finding in analysis.findings:
        if finding.category not in FOCUS:
            continue
        valid = bool(finding.evidence)
        for ref in finding.evidence:
            block = blocks[positions[ref.block_id]] if ref.block_id in positions else None
            source = sources.get(block.source_id) if block else None
            if (
                not block
                or not source
                or source.publication_date > analysis.as_of
                or not normalize(ref.quote)
                or normalize(ref.quote) not in normalize(block.text)
            ):
                valid = False
        if not valid:
            omitted.append(finding.id)
            continue
        anchor = min((r.block_id for r in finding.evidence), key=positions.__getitem__)
        groups.setdefault(anchor, []).append(finding)

    def packet(items: list) -> dict:
        spans: dict[int, tuple[int, int]] = {}

        def include(index: int, start: int, end: int) -> None:
            previous = spans.get(index, (start, end))
            spans[index] = (min(start, previous[0]), max(end, previous[1]))

        for f in items:
            for ref in f.evidence:
                i = positions[ref.block_id]
                include(i, 0, len(blocks[i].text.splitlines()))
                for j in (i - 1, i + 1):
                    if 0 <= j < len(blocks) and blocks[j].source_id == blocks[i].source_id:
                        lines = blocks[j].text.splitlines()
                        include(
                            j,
                            max(0, len(lines) - 14) if j < i else 0,
                            len(lines) if j < i else min(14, len(lines)),
                        )
        context = []
        for i in sorted(spans):
            start, end = spans[i]
            item = blocks[i].model_dump()
            item["text"] = "\n".join(blocks[i].text.splitlines()[start:end])
            item["excerpt_line_start"] = blocks[i].line_start + start
            item["excerpt_line_end"] = blocks[i].line_start + end - 1
            context.append(item)
        return {
            "as_of": analysis.as_of.isoformat(),
            "company": analysis.company,
            "request": REQUEST,
            "findings": [
                {
                    "id": f.id,
                    "category": f.category,
                    "evidence": [r.model_dump() for r in f.evidence],
                }
                for f in items
            ],
            "blocks": context,
        }

    result, current = [], []
    for anchor in sorted(groups, key=positions.__getitem__):
        # A very dense block may require splitting the candidate list, not the evidence.
        for finding in groups[anchor]:
            proposal = current + [finding]
            if len(json.dumps(packet(proposal), ensure_ascii=False)) <= max_chars:
                current = proposal
                continue
            if current:
                result.append(packet(current))
                current = []
            single = packet([finding])
            if len(json.dumps(single, ensure_ascii=False)) > max_chars:
                omitted.append(finding.id)
            else:
                current = [finding]
    if current:
        result.append(packet(current))
    return result, omitted


def _contains(name: str, refs: list[Locator]) -> bool:
    return bool(name) and any(
        re.search(rf"(?<!\w){re.escape(normalize(name))}(?!\w)", normalize(r.quote), re.I)
        for r in refs
    )


def _company_key(name: str) -> str:
    value = normalize(name).casefold().rstrip(" .,")
    return re.sub(r",?\s+(?:corp(?:oration)?|inc(?:orporated)?|plc|ltd|limited)$", "", value)


def _same_reporter(name: str, reporter: str) -> bool:
    given = normalize(name).casefold().rstrip(" .,")
    full = normalize(reporter).casefold().rstrip(" .,")
    # Accept the actual full name or its short form. Two different legal forms
    # sharing a stem (e.g. Acme Inc vs Acme Ltd) are not equated.
    return given in {full, _company_key(reporter)}


def classify(draft: RelationDraft) -> tuple[str, str, str]:
    """Named deterministic rules; no votes, weights, severity score or company names."""
    primary = (draft.executive_link, draft.transaction, draft.same_parties)
    transaction_text = " ".join(r.quote for r in draft.transaction.evidence)
    routine_contract = re.search(
        r"\b(?:employment|consulting services|executive employment) agreement\b",
        transaction_text,
        re.I,
    )
    if draft.kind == "employment" or routine_contract:
        return (
            "context",
            "routine_contract",
            "İş/ücret veya danışmanlık sözleşmesi tek başına karşı tarafta yönetim bağlantısını göstermez.",
        )
    if draft.kind == "unresolved" or any(c.answer == "conflicting" for c in primary):
        return (
            "unassessed",
            "unresolved_relation",
            "Taraf/rol/işlem bağlantısı belirsiz veya çelişkili; öncelik belirlenemedi.",
        )
    if all(c.answer == "yes" for c in primary):
        return (
            "first_review",
            "executive_linked_transaction",
            "Yönetici bağlantısı ile aynı karşı tarafla yapılan işlem birlikte kaynaklandırıldı. İşlem koşullarının bağımsızlığı ve açıklanan kontroller incelenmeli.",
        )
    if draft.transaction.answer == "yes" and draft.kind == "related_transaction":
        return (
            "further_review",
            "related_transaction",
            "İlişkili işlem açıklaması var; yönetici–karşı taraf bağlantısının bütün koşulları tamamlanmadı.",
        )
    if draft.kind in {"ownership", "executive_relationship"}:
        return (
            "context",
            "relationship_only",
            "İlişki açıklaması var; aynı ilişkiyle bağlantılı işlem bu değerlendirmede tamamlanmadı.",
        )
    return (
        "unassessed",
        "insufficient_evidence",
        "İlişkiyi ve işlemi sınıflandırmak için yeterli açıklık sağlanamadı.",
    )


def validate_review(review: RelationReview, packet: dict) -> tuple[list[ReviewCase], list[dict]]:
    inputs = {f["id"]: f for f in packet["findings"]}
    blocks = {b["id"]: b["text"] for b in packet["blocks"]}
    occurrences = Counter(fid for c in review.cases for fid in c.finding_ids)
    accepted, rejected = [], []
    for draft in review.cases:
        refs = _references(draft)
        reason = ""
        if any(fid not in inputs or occurrences[fid] != 1 for fid in draft.finding_ids):
            reason = "unknown_or_repeated_finding_id"
        elif any(
            not normalize(r.quote)
            or len(normalize(r.quote)) < 12
            or normalize(r.quote) not in normalize(blocks.get(r.block_id, ""))
            for r in refs
        ):
            reason = "quote_not_in_supplied_block"
        elif any(
            getattr(draft, key).answer != "unknown" and not getattr(draft, key).evidence
            for key in CHECKS
        ):
            reason = "check_without_evidence"
        elif any(
            name and not _contains(name, refs)
            for name in (draft.company_name, draft.counterparty, draft.executive)
        ):
            reason = "name_not_in_evidence"
        elif draft.company_name and not _same_reporter(draft.company_name, packet["company"]):
            reason = "reporting_company_mismatch"
        elif any(
            not any(
                r.block_id == original["block_id"]
                and (
                    normalize(r.quote) in normalize(original["quote"])
                    or normalize(original["quote"]) in normalize(r.quote)
                )
                for r in refs
                for original in inputs[fid]["evidence"]
            )
            for fid in draft.finding_ids
        ):
            reason = "unrelated_finding_evidence"
        elif draft.same_parties.answer == "yes" and (
            not _contains(draft.company_name, draft.transaction.evidence)
            or not _contains(draft.counterparty, draft.transaction.evidence)
            or not _contains(
                draft.counterparty, draft.executive_link.evidence + draft.same_parties.evidence
            )
            or not _contains(draft.executive, draft.executive_link.evidence)
        ):
            reason = "party_identity_not_grounded"
        elif draft.controls.answer == "unknown" and draft.control_basis != "not_found":
            reason = "control_basis_without_disclosure"
        elif draft.controls.answer == "yes" and draft.control_basis == "not_found":
            reason = "control_disclosure_without_basis"
        elif draft.control_basis == "reported_independent" and not re.search(
            r"\bindependent\b|\boutside (?:apprais|valu)|\baudit committee\b",
            " ".join(r.quote for r in draft.controls.evidence),
            re.I,
        ):
            reason = "independent_control_not_grounded"
        elif draft.executive_link.answer == "yes" and any(
            re.search(
                r"\b(?:does|did|do|is|was|are|were)\s+not\b[^.;]{0,80}\b(?:manag\w*|control\w*|director|officer|own\w*)\b",
                normalize(r.quote),
                re.I,
            )
            for r in draft.executive_link.evidence
        ):
            reason = "negated_executive_role"
        if reason:
            rejected.append({"reason": reason, "finding_ids": draft.finding_ids})
            continue
        priority, rule, explanation = classify(draft)
        fid = digest(("|".join(sorted(draft.finding_ids)) + ":" + rule).encode())[:24]
        unknowns = [
            CHECK_LABELS[k]
            for k in CHECKS
            if getattr(draft, k).answer in {"unknown", "conflicting"}
        ]
        accepted.append(
            ReviewCase(
                id="relation_" + fid,
                priority=priority,
                rule_id=rule,
                title=(draft.counterparty + ": " if draft.counterparty else "")
                + {
                    "first_review": "yönetici bağlantılı işlem",
                    "further_review": "ilişkili işlem",
                    "context": "ilişki / sözleşme açıklaması",
                    "unassessed": "ilişki değerlendirmesi eksik",
                }[priority],
                explanation=explanation,
                source_finding_ids=sorted(draft.finding_ids),
                supporting_evidence=_unique(
                    draft.classification_evidence
                    + [r for k in CHECKS for r in getattr(draft, k).evidence]
                ),
                counter_evidence=_unique(draft.counter_evidence),
                unknowns=unknowns,
                model_assessed=True,
                relation=draft,
            )
        )
    return accepted, rejected


def _unassessed(fid: str, reason: str, analysis: Analysis) -> ReviewCase:
    finding = next(f for f in analysis.findings if f.id == fid)
    return ReviewCase(
        id="unassessed_" + fid,
        priority="unassessed",
        rule_id="not_assessed",
        title=finding.title,
        explanation=reason,
        source_finding_ids=[fid],
        supporting_evidence=finding.evidence,
        unknowns=["İlişki/işlem değerlendirmesi tamamlanmadı."],
    )


def _numeric_cases(analysis: Analysis) -> list[ReviewCase]:
    facts = {f.id: f for f in analysis.facts}
    result = []
    for f in analysis.findings:
        if f.category not in {"financial", "data_quality"}:
            continue
        explanation = f.explanation
        if f.id.startswith("cash_profit_divergence_"):
            explanation = "Kâr artarken faaliyet nakdi azalmış. Ayrışmanın nedeni mevcut hesaplamalarda açıklanmadı; nakit akışı kalemleri incelenmeli."
        extra_refs = []
        if f.id.startswith("current_ratio_"):
            current = [m for m in analysis.metrics if m.id.startswith("current_ratio_")]
            latest = max(current, key=lambda m: m.period, default=None)
            original = next((m for m in current if m.id == f.id), None)
            if latest and original and latest.period > original.period:
                explanation += f" Son kayıtlı dönemde ({latest.period}) cari oran {latest.value:.3f}; önceki dönem işareti güncel dönemle birlikte okunmalı."
                extra_refs = [facts[i].evidence for i in latest.fact_ids if i in facts]
        result.append(
            ReviewCase(
                id="numeric_" + f.id,
                priority="further_review"
                if f.status == "signal"
                else "context"
                if f.status == "context"
                else "unassessed",
                rule_id=f.id,
                title=f.title,
                explanation=explanation,
                source_finding_ids=[f.id],
                supporting_evidence=_unique(
                    f.evidence + [facts[i].evidence for i in f.fact_ids if i in facts] + extra_refs
                ),
            )
        )
    return result


def _merge_and_sort(cases: list[ReviewCase], analysis: Analysis) -> list[ReviewCase]:
    groups: dict[tuple, ReviewCase] = {}
    for case in cases:
        d = case.relation
        key = (case.id,)
        if d and case.priority == "first_review":
            # One relationship/transaction block is one issue, however many quotes mention it.
            key = (
                case.priority,
                normalize(d.company_name).casefold(),
                normalize(d.counterparty).casefold(),
                normalize(d.executive).casefold(),
                tuple(sorted({r.block_id for r in d.transaction.evidence})),
            )
        if key not in groups:
            groups[key] = case
        else:
            target = groups[key]
            target.source_finding_ids = sorted(
                set(target.source_finding_ids + case.source_finding_ids)
            )
            target.supporting_evidence = _unique(
                target.supporting_evidence + case.supporting_evidence
            )
            target.counter_evidence = _unique(target.counter_evidence + case.counter_evidence)
            target.unknowns = sorted(set(target.unknowns + case.unknowns))
            if target.relation and d:
                target.relation.finding_ids = target.source_finding_ids
                target.relation.counter_evidence = target.counter_evidence
                target.relation.classification_evidence = _unique(
                    target.relation.classification_evidence + d.classification_evidence
                )
                for name in CHECKS:
                    a, b = getattr(target.relation, name), getattr(d, name)
                    if a.answer == "unknown":
                        setattr(target.relation, name, b)
                    elif b.answer != "unknown":
                        a.evidence = _unique(a.evidence + b.evidence)
                        if a.answer != b.answer:
                            a.answer = "conflicting"
                bases = {target.relation.control_basis, d.control_basis} - {"not_found"}
                target.relation.control_basis = (
                    next(iter(bases))
                    if len(bases) == 1
                    else "conflicting"
                    if bases
                    else "not_found"
                )
                target.unknowns = [
                    CHECK_LABELS[k]
                    for k in CHECKS
                    if getattr(target.relation, k).answer in {"unknown", "conflicting"}
                ]
    for case in groups.values():
        if case.model_assessed:
            case.id = (
                "relation_"
                + digest(("|".join(sorted(case.source_finding_ids)) + ":" + case.rule_id).encode())[
                    :24
                ]
            )
    positions = {b.id: i for i, b in enumerate(analysis.blocks)}
    order = {"first_review": 0, "further_review": 1, "context": 2, "unassessed": 3}
    return sorted(
        groups.values(),
        key=lambda c: (
            order[c.priority],
            min((positions.get(r.block_id, 10**9) for r in c.supporting_evidence), default=10**9),
            c.id,
        ),
    )


def render_assessment(result: Assessment, analysis: Analysis) -> str:
    def inline(value: str) -> str:
        return re.sub(r"([\\`*_\[\]{}()#+!|])", r"\\\1", escape(normalize(value), quote=False))

    lines = [
        f"# {inline(result.company)} — inceleme öncelikleri",
        "",
        f"Bilgi kesimi: {result.as_of}. Durum: **{result.status}**. Kaynak analiz: `{result.source_run_id}` ({result.source_analysis_status}).",
        "",
        "Bu rapor otomatik bir inceleme önerisidir; şirket risk sınıfı veya risk yüzdesi değildir. Aynı öncelik içindeki sıra kaynak konumuna aittir.",
        "",
        "## İlk inceleme konuları",
        "",
    ]
    top = [c for c in result.cases if c.priority in {"first_review", "further_review"}][:3]
    lines.extend(
        f"{i}. **{inline(c.title)}** — {PRIORITY_LABELS[c.priority]}. {c.explanation}"
        for i, c in enumerate(top, 1)
    )
    if not top:
        lines.append(
            "Öncelikli/ek inceleme konusu üretilemedi; değerlendirilmemiş kapsam aşağıdadır."
        )
    for priority, label in PRIORITY_LABELS.items():
        lines.extend(["", f"## {label}", ""])
        selected = [c for c in result.cases if c.priority == priority]
        if not selected:
            lines.append("Bu grupta kayıt yok.")
        for case in selected:
            lines.extend(
                [
                    f"### {inline(case.title)}",
                    "",
                    case.explanation,
                    "",
                    f"Kural: `{case.rule_id}`. Model değerlendirmesi: {case.model_assessed}; insan onayı: {case.human_reviewed}.",
                    "",
                    "Kaynak bulgular: " + ", ".join(f"`{fid}`" for fid in case.source_finding_ids),
                    "",
                ]
            )
            if case.relation:
                lines.extend(
                    f"- {CHECK_LABELS[k]}: {ANSWER_LABELS[getattr(case.relation, k).answer]}"
                    for k in CHECKS
                )
                lines.append(
                    f"- Kontrol açıklamasının dayanağı: `{case.relation.control_basis}`. Bağımsız doğrulama yapılmış sayılmaz."
                )
            if case.unknowns:
                lines.extend(["", "Bilinmeyen / çelişkili: " + "; ".join(case.unknowns), ""])
            for heading, refs in (
                ("Destekleyen kaynak pasajları", case.supporting_evidence),
                ("Dengeleyici kaynak pasajları", case.counter_evidence),
            ):
                if refs:
                    lines.extend(["", f"**{heading}**", ""])
                for ref in refs:
                    lines.extend([f"Blok: `{ref.block_id}`", "", literal(ref.quote), ""])
    lines.extend(
        [
            "",
            "## Korunan sayısal göstergeler",
            "",
            "| Dönem | Gösterge | Değer | Birim |",
            "|---|---|---:|---|",
        ]
    )
    lines.extend(f"| {m.period} | {m.name} | {m.value:.4f} | {m.unit} |" for m in analysis.metrics)
    lines.extend(["", "## Kaynaklar", ""])
    lines.extend(
        f"- {s.url} — yayın {s.publication_date}; SHA-256 `{s.sha256}`." for s in analysis.sources
    )
    lines.extend(
        [
            "",
            "## Kapsam ve sınırlar",
            "",
            literal(json.dumps(result.coverage, ensure_ascii=False, indent=2)),
            "",
        ]
    )
    lines.extend(f"- {item}" for item in result.limitations)
    lines.append(
        f"- Kapsam dışındaki özgün AI bulguları: {len(result.out_of_scope_finding_ids)}. Tamamı kaynak analizde korunuyor."
    )
    if result.rejected:
        lines.append(
            f"- {len(result.rejected)} model çıktısı reddedildi; gerekçeler assessment.json içinde."
        )
    lines.extend(
        [
            "",
            f"Değerlendirme: `{result.id}`. Kaynak analiz özeti SHA-256: `{result.source_analysis_sha256}`.",
            "",
        ]
    )
    return "\n".join(lines)


def run_assessment(
    settings: Settings,
    store: Store,
    analysis: Analysis,
    *,
    remaining_calls: int | None = None,
    codex: Codex | None = None,
    progress: Callable[[str], None] = lambda _: None,
) -> Assessment:
    started = time.perf_counter()
    result = Assessment(
        id=str(uuid.uuid4()),
        source_run_id=analysis.run_id,
        source_analysis_sha256=analysis_digest(analysis),
        company=analysis.company,
        as_of=analysis.as_of,
        created_at=datetime.now(UTC),
        source_analysis_status=analysis.status,
        limitations=list(dict.fromkeys(BOUNDARIES + analysis.limitations)),
    )
    directory = settings.data_dir / "assessments" / result.id
    store.start_assessment(result)
    directory.mkdir(parents=True, exist_ok=False)
    ai = codex or Codex(settings, directory / "ai")
    call_start = ai.calls
    budget = min(
        8,
        settings.max_ai_calls,
        max(0, remaining_calls if remaining_calls is not None else settings.max_ai_calls),
    )
    focus_ids = {f.id for f in analysis.findings if f.category in FOCUS}
    result.out_of_scope_finding_ids = [
        f.id for f in analysis.findings if f.category not in FOCUS | {"financial", "data_quality"}
    ]
    result.cases = _numeric_cases(analysis)
    examined, total, failed, consecutive_errors = 0, 0, 0, 0
    try:
        if not analysis.sources or analysis.status == "failed":
            raise ValueError("Kullanılabilir kaynak analizi yok.")
        packages, omitted = make_packages(analysis, settings.chunk_chars)
        total = len(packages)
        for index, packet in enumerate(packages, 1):
            if ai.calls - call_start >= budget:
                result.limitations.append(
                    "Değerlendirme çağrı bütçesi doldu; eksik adaylar normal kabul edilmedi."
                )
                break
            progress(f"assessment {index}/{total}")
            write_json(
                directory / "checkpoint.json",
                {"id": result.id, "package": index, "total": total, "status": "running"},
            )
            if any(
                re.search(
                    r"ignore (?:all |the )?(?:previous|system) instructions|<system>|reveal (?:your )?(?:secret|api key)",
                    b["text"],
                    re.I,
                )
                for b in packet["blocks"]
            ):
                result.limitations.append(
                    "Paket talimat benzeri metin içeriyor; modele gönderilmedi."
                )
                continue
            try:
                review = ai.assess_relations(packet)
                consecutive_errors = 0
            except AIError as exc:
                failed += 1
                consecutive_errors += 1
                result.limitations.append(
                    f"Paket {index} model değerlendirmesi tamamlanamadı: {exc}"
                )
                # No retry of this packet. Other independent packets may still
                # succeed, but policy violations or repeated errors halt the stage.
                if any(
                    word in str(exc).casefold()
                    for word in ("araç", "protokol", "bütçe", "başlatılamadı")
                ):
                    raise
                if consecutive_errors >= 2:
                    result.limitations.append(
                        "Üst üste iki model hatası; kalan çağrılar yapılmadı."
                    )
                    break
                continue
            accepted, rejected = validate_review(review, packet)
            result.cases.extend(accepted)
            result.rejected.extend(rejected)
            examined += 1
        if omitted:
            result.limitations.append(
                f"{len(omitted)} adayın kaynak/tarih/paket boyutu kontrolü geçmedi."
            )
        result.status = "complete"
    except KeyboardInterrupt:
        result.limitations.append("Değerlendirme kesildi; kaynak analiz korunuyor.")
        result.status = "partial"
    except AIError as exc:
        result.limitations.append(f"Model değerlendirmesi tamamlanamadı: {exc}")
        result.status = "partial"
    except Exception as exc:
        result.limitations.append(
            f"Değerlendirme tamamlanamadı ({type(exc).__name__}); kaynak analiz korunuyor."
        )
        result.status = "failed"
    completed = {fid for c in result.cases if c.model_assessed for fid in c.source_finding_ids}
    missing = focus_ids - completed
    for fid in sorted(missing):
        result.cases.append(
            _unassessed(
                fid, "Model cevabı alınamadı veya kaynak/kimlik denetimini geçmedi.", analysis
            )
        )
    if missing or result.rejected:
        if result.status == "complete":
            result.status = "partial"
    result.cases = _merge_and_sort(result.cases, analysis)
    result.coverage = {
        "focused_candidates": len(focus_ids),
        "assessed_candidates": len(completed),
        "unassessed_candidates": len(missing),
        "total_packages": total,
        "examined_packages": examined,
        "failed_packages": failed,
        "call_budget": budget,
        "out_of_scope_candidates": len(result.out_of_scope_finding_ids),
    }
    result.ai = {
        "calls": ai.calls - call_start,
        "receipts": ai.receipts[call_start:],
        "web_search": False,
    }
    result.timings["total"] = round(time.perf_counter() - started, 4)
    write_json(directory / "assessment.json", result.model_dump(mode="json"))
    atomic_write(directory / "assessment.md", render_assessment(result, analysis).encode())
    store.finish_assessment(result)
    write_json(
        directory / "checkpoint.json",
        {"id": result.id, "status": result.status, "stage": "finished"},
    )
    return result
