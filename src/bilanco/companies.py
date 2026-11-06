"""Local issuer registry. Models suggest a KAP URL; Python derives the identity."""

import json
import re
from datetime import UTC, datetime

from pydantic import Field

from .equity_discovery import kap_id
from .equity_models import COMPANIES, ISTANBUL, Company
from .equity_sources import KAP, EquityHTTP, accept_kap, fold
from .models import Model
from .storage import digest, write_json


class CompanyError(ValueError):
    pass


class CompanyRecord(Model):
    schema_version: str = "1.0"
    company: Company
    disclosure_id: int = Field(gt=0)
    verified_at: datetime
    metadata_sha256: str
    pdf_sha256: str
    source_url: str
    limitations: list[str]


def ticker(value):
    value = value.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{2,5}", value):
        raise CompanyError(
            "BIST hisse kodunu yazın; örnek: THYAO. Şirket adını önce koda eşleştirin."
        )
    return value


def metadata_identity(raw, disclosure_id, expected_ticker):
    try:
        rows = json.loads(raw)
        if not isinstance(rows, list) or len(rows) != 1:
            raise ValueError
        basic = rows[0]["disclosure"]["disclosureBasic"]
        name, member = basic["companyTitle"], basic["mkkMemberOid"]
        codes = re.split(r"[^A-Z0-9]+", basic["stockCode"])
        if (
            int(basic["disclosureIndex"]) != disclosure_id
            or expected_ticker not in codes
            or not isinstance(name, str)
            or not 12 <= len(name.strip()) <= 250
            or not re.fullmatch(r"[a-fA-F0-9]{32}", member)
        ):
            raise ValueError
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise CompanyError(
            "KAP bildiriminde istenen kod, unvan veya üye kimliği doğrulanamadı."
        ) from exc
    return Company(
        id=expected_ticker.lower(),
        name=name.strip(),
        identity=fold(name),
        ticker=expected_ticker,
        kap_member=member.lower(),
        identity_disclosure_id=disclosure_id,
        listed_at=None,
    )


def register_company(settings, expected_ticker, url, *, http=None):
    code = ticker(expected_ticker)
    if code.lower() in COMPANIES:
        raise CompanyError("Şirket yerleşik listede zaten var; kayıt üzerine yazılmadı.")
    index = kap_id(url)
    client = http or EquityHTTP(settings)
    try:
        raw = client.request(f"{KAP}/tr/api/notification/attachment-detail/{index}")
        company = metadata_identity(raw, index, code)
        pdf = client.request(f"{KAP}/tr/api/BildirimPdf/{index}")
        # Own PDF must prove the complete issuer name, notification ID and publication time.
        accept_kap(pdf, index, company, datetime.now(ISTANBUL).date(), settings, persist=False)
        record = CompanyRecord(
            company=company,
            disclosure_id=index,
            verified_at=datetime.now(UTC),
            metadata_sha256=digest(raw),
            pdf_sha256=digest(pdf),
            source_url=f"{KAP}/tr/Bildirim/{index}",
            limitations=[
                "Kimlik belgesi yalnız yönlendirme içindir; geçmiş finansal kanıt değildir.",
                "İlk işlem tarihi doğrulanmadı. Geçmiş kod/unvan değişimleri otomatik birleştirilmez.",
                "Şirketin bulunması bütün sektör raporlarının desteklendiğini göstermez.",
            ],
        )
        path = settings.data_dir / "companies" / f"{company.id}.json"
        if path.exists():
            old = _load_record(settings, path)
            if old.company.kap_member != company.kap_member:
                raise CompanyError("Kayıtlı şirket kimliği farklı; otomatik üzerine yazılmadı.")
        # Preserve the evidence even with an injected HTTP test adapter.
        from .storage import atomic_write

        atomic_write(settings.data_dir / "raw" / digest(raw), raw)
        atomic_write(settings.data_dir / "raw" / digest(pdf), pdf)
        write_json(path, record.model_dump(mode="json"))
        return record
    finally:
        if http is None:
            client.close()


def _load_record(settings, path):
    try:
        if path.stat().st_size > 50_000:
            raise ValueError
        record = CompanyRecord.model_validate_json(path.read_text())
        company = record.company
        if (
            record.schema_version != "1.0"
            or company.id != ticker(company.ticker).lower()
            or path.stem != company.id
            or company.identity_disclosure_id != record.disclosure_id
            or company.listed_at is not None
            or record.verified_at.tzinfo is None
            or record.source_url != f"{KAP}/tr/Bildirim/{record.disclosure_id}"
        ):
            raise ValueError
        evidence = []
        for sha in (record.metadata_sha256, record.pdf_sha256):
            if not re.fullmatch(r"[0-9a-f]{64}", sha):
                raise ValueError
            raw_path = settings.data_dir / "raw" / sha
            if raw_path.stat().st_size > settings.max_download_bytes:
                raise ValueError
            raw = raw_path.read_bytes()
            if digest(raw) != sha:
                raise ValueError
            evidence.append(raw)
        expected = metadata_identity(evidence[0], record.disclosure_id, company.ticker)
        if expected != company:
            raise ValueError
        # The accepted PDF is rechecked without HTTP or any model call.
        accept_kap(
            evidence[1],
            record.disclosure_id,
            company,
            record.verified_at.astimezone(ISTANBUL).date(),
            settings,
            persist=False,
        )
        return record
    except (OSError, ValueError, TypeError) as exc:
        raise CompanyError(
            "Yerel şirket kaydı veya kimlik kanıtı doğrulanamadı; yeniden kayıt gerekli."
        ) from exc


def get_company(settings, query):
    key = ticker(query).lower()
    if key in COMPANIES:
        return COMPANIES[key]
    path = settings.data_dir / "companies" / f"{key}.json"
    if not path.is_file():
        raise CompanyError(
            f"{key.upper()} kayıtlı değil. Codex/kullanıcı resmî KAP bildirim bağlantısını bulup "
            f"bilanco company add --ticker {key.upper()} --kap-url URL çalıştırmalı."
        )
    return _load_record(settings, path).company


def all_companies(settings):
    result = dict(COMPANIES)
    for path in sorted((settings.data_dir / "companies").glob("*.json")):
        record = _load_record(settings, path)
        if record.company.id not in result:
            result[record.company.id] = record.company
    return result
