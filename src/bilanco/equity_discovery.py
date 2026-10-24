"""Web results are routing suggestions, never financial evidence or publication proof."""

import re
from urllib.parse import urlsplit

import httpx
from pydantic import Field

from .ai import AIError, safe_error
from .equity_models import Company
from .equity_sources import (
    KAP,
    Dataset,
    EquityHTTP,
    accept_attachment,
    accept_kap,
    attachment_metadata,
    document_blocks,
    fold,
)
from .models import Model


class SourceProposal(Model):
    url: str
    target: str
    entity_name: str


class TurkeyDiscovery(Model):
    sources: list[SourceProposal] = Field(max_length=5)


def kap_id(url):
    p = urlsplit(url)
    if (
        p.scheme != "https"
        or p.hostname not in {"kap.org.tr", "www.kap.org.tr"}
        or p.port not in (None, 443)
        or p.username
        or p.password
        or p.query
        or p.fragment
    ):
        raise ValueError("Yalnız özgün KAP bildirim adresi kabul edilir.")
    match = re.fullmatch(r"/tr/(?:Bildirim|api/BildirimPdf)/([1-9][0-9]{0,8})/?", p.path, re.I)
    if not match:
        raise ValueError("Tarihi doğrulanabilir KAP bildirim numarası gerekli.")
    return int(match[1])


def fund_targets(analysis):
    return sorted(
        {
            f.subject
            for f in analysis.document_facts
            if f.kind == "fund_position" and re.fullmatch(r"[A-Z0-9]{3,5}", f.subject)
        }
    )[:4]


def accept_proposal(raw, proposal, company, codes, as_of, settings, disclosure_id):
    if proposal.target == "issuer":
        return accept_kap(raw, disclosure_id, company, as_of, settings)
    if proposal.target not in codes:
        raise ValueError("Fon kodu tarihli şirket belgesinde kanıtlanmadı.")
    if len(proposal.entity_name) < 12 or "fon" not in fold(proposal.entity_name):
        raise ValueError("Fonun açık tüzel adı gerekli.")
    blocks, _ = document_blocks(raw, "identity-check")
    # Only the cover before the publication footer proves the issuing fund.
    # A code buried in a portfolio table is not the report owner's identity.
    cover = "\n".join(b.text for b in blocks if b.page == 1)
    cover = re.split(r"KAP.t[ae] yay", cover, maxsplit=1, flags=re.I)[0]
    code = re.escape(proposal.target)
    if not re.search(rf"(?:^|\n)\s*(?:Fon Kodu\s*:\s*)?{code}\s*(?:\n|$)", cover, re.I):
        raise ValueError("Fonun kendi kapak kodu doğrulanmadı; portföy satırı kimlik değildir.")
    entity = Company(
        id=proposal.target.lower(),
        name=proposal.entity_name,
        identity=fold(proposal.entity_name),
        ticker=proposal.target,
        listed_at=company.listed_at,
    )
    source, blocks, issues = accept_kap(raw, disclosure_id, entity, as_of, settings)
    source.role = "related_fund"
    source.kind = "fund_disclosure"
    return source, blocks, issues


def discover_sources(ai, settings, company, analysis, *, http=None):
    codes = fund_targets(analysis)
    audit = {
        "enabled": True,
        "status": "failed",
        "targets": ["issuer", *codes],
        "proposals": [],
        "accepted": 0,
        "note": "Güncel web araması tam kör deney değildir. Yalnız tarih/kimlik doğrulanan özgün belge içeriği işlenir.",
    }
    data = Dataset()
    try:
        packet = {
            "company": company.name,
            "ticker": company.ticker,
            "as_of": analysis.as_of.isoformat(),
            "supported_hosts": ["www.kap.org.tr", "kap.org.tr"],
            "fund_codes_from_accepted_historical_evidence": codes,
            "known_disclosure_ids": sorted(
                {s.disclosure_id for s in analysis.sources if s.disclosure_id}
            ),
            "request": (
                "Find at most five original KAP notification URLs published on/before as_of. "
                "Prioritize the identified funds' OWN historical financial reports, portfolio/net asset value reports "
                "and redemption/issue documents, then missing issuer activity/financial reports. "
                "target must be issuer or one of supplied fund codes. entity_name is the full publishing entity name. "
                "Return no values, facts, dates, verdicts or subsequent events. Do not search for fraud, scandals or collapse. "
                "Use neutral document queries with fund code and historical year. "
                "No current-only pages, TEFAS current values, news, comments or invented URLs. "
                "Empty sources is allowed. Do not repeat known notification IDs. "
                "A candidate will be rejected unless its own KAP PDF independently proves code, name and publication time."
            ),
        }
        result = ai.ask("tr_discover_sources_v1", packet, TurkeyDiscovery, discovery=True)
        audit["initial_proposals"] = len(result.sources)
        if not result.sources and hasattr(ai, "escalate"):
            try:
                stronger = ai.escalate(
                    "tr_discover_sources_v1",
                    packet,
                    TurkeyDiscovery,
                    from_model=getattr(ai, "last_model", None),
                    discovery=True,
                    reason="empty_discovery_coverage_retry",
                )
                if stronger is not None:
                    audit["coverage_retry"] = "empty_search_is_not_a_validation_error"
                    result = stronger
            except AIError as exc:
                audit["coverage_retry_error"] = safe_error(str(exc))

    except AIError as exc:
        audit["error"] = safe_error(str(exc))
        return data, audit
    owned = http is None
    http = http or EquityHTTP(settings)
    seen = {s.disclosure_id for s in analysis.sources}
    try:
        for proposal in result.sources:
            record = {**proposal.model_dump(), "status": "rejected"}
            audit["proposals"].append(record)
            try:
                if proposal.target not in {"issuer", *codes}:
                    raise ValueError("Tarihsel kanıtla bağlı olmayan arama hedefi.")
                notification = kap_id(proposal.url)
                record["disclosure_id"] = notification
                if notification in seen:
                    record["status"] = "duplicate"
                    continue
                seen.add(notification)
                raw = http.request(f"{KAP}/tr/api/BildirimPdf/{notification}")
                source, blocks, issues = accept_proposal(
                    raw, proposal, company, codes, analysis.as_of, settings, notification
                )
                data.sources.append(source)
                data.blocks.extend(blocks)
                data.issues.extend(issues)
                record.update(status="accepted", source_id=source.id)
                audit["accepted"] += 1
                record["attachments"] = []
                try:
                    entries = attachment_metadata(
                        http.request(f"{KAP}/tr/api/notification/attachment-detail/{notification}"),
                        source,
                        analysis.as_of,
                    )
                    entity = (
                        company
                        if source.role == "issuer"
                        else Company(
                            id=source.entity_code.lower(),
                            name=source.entity_name,
                            identity=fold(source.entity_name),
                            ticker=source.entity_code,
                            listed_at=company.listed_at,
                        )
                    )
                    for entry in entries[:10]:
                        oid = str(entry.get("objId", ""))
                        if (
                            not re.fullmatch(r"[0-9a-fA-F]{32}", oid)
                            or str(entry.get("fileExtension", "")).lower() != "pdf"
                        ):
                            continue
                        item = {"obj_id": oid, "status": "rejected"}
                        record["attachments"].append(item)
                        try:
                            child, child_blocks, child_issues = accept_attachment(
                                http.request(f"{KAP}/tr/api/file/download/{oid}"),
                                entry,
                                source,
                                entity,
                                settings,
                            )
                            if source.role == "related_fund":
                                child.kind = "fund_attachment"
                            if child.id in {
                                s.id for s in [*analysis.sources, *data.sources]
                            } or child.sha256 in {
                                s.sha256 for s in [*analysis.sources, *data.sources]
                            }:
                                item["status"] = "duplicate"
                                continue
                            data.sources.append(child)
                            data.blocks.extend(child_blocks)
                            data.issues.extend(child_issues)
                            item.update(status="accepted", source_id=child.id)
                        except (ValueError, OSError, KeyError, TypeError, httpx.HTTPError) as exc:
                            item["reason"] = safe_error(str(exc))
                            data.issues.append(
                                f"{source.id}: keşfedilen ek alınamadı ({type(exc).__name__})."
                            )
                    if len(entries) > 10:
                        data.issues.append(
                            f"{source.id}: keşif ekleri 10 belgeyle sınırlı; kalan ekler incelenmedi."
                        )
                except (ValueError, OSError, KeyError, TypeError, httpx.HTTPError) as exc:
                    record["attachment_error"] = safe_error(str(exc))
                    data.issues.append(
                        f"{source.id}: keşif ek kapsamı alınamadı ({type(exc).__name__})."
                    )
            except (ValueError, OSError, httpx.HTTPError) as exc:
                record["reason"] = safe_error(str(exc))
    finally:
        if owned:
            http.close()
    audit["status"] = "completed"
    audit["accepted_documents"] = len(data.sources)
    return data, audit
