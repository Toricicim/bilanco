"""Bounded public-source acquisition and independently dated manual KAP imports."""

import csv
import io
import json
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .config import Settings
from .documents import read_document
from .equity_models import (
    ISTANBUL,
    Bundle,
    Company,
    EquitySource,
    MarketSeries,
    PriceBar,
    available_at,
    cutoff,
)
from .models import Block, Source
from .storage import atomic_write, digest, write_json

KAP = "https://www.kap.org.tr"
SPK_2025 = "https://spk.gov.tr/data/68126e9e8f95db0ba8ec02f2/2025-28.pdf"
HOSTS = {"www.kap.org.tr", "kap.org.tr", "spk.gov.tr", "www.spk.gov.tr", "query1.finance.yahoo.com"}


def fold(value: str) -> str:
    value = value.translate(str.maketrans({"ı": "i", "İ": "I", "’": "'", "‘": "'", "ʼ": "'"}))
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9%.,]+", " ", value).split())


def safe_url(url: str) -> bool:
    try:
        p = urlsplit(url)
        return (
            p.scheme == "https"
            and p.hostname in HOSTS
            and p.port in (None, 443)
            and not p.username
            and not p.password
            and not p.fragment
            and len(url) < 4096
            and not any(ord(c) < 33 for c in url)
        )
    except ValueError:
        return False


def public_date(text: str) -> datetime:
    if not isinstance(text, str):
        raise ValueError("KAP yayın zamanı metin olmalı.")
    for pattern in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%Y.%m.%d %H:%M:%S"):
        try:
            return datetime.strptime(text.strip(), pattern).replace(tzinfo=ISTANBUL)
        except ValueError:
            pass
    raise ValueError("KAP yayın zamanı okunamadı.")


def local_file(root: Path, name: str, maximum: int) -> bytes:
    file = (root / name).resolve()
    if not file.is_relative_to(root.resolve()) or not file.is_file():
        raise ValueError("Paket dışına çıkan veya bulunamayan dosya.")
    if file.stat().st_size > maximum:
        raise ValueError("Paket dosyası boyut sınırını aşıyor.")
    return file.read_bytes()


class EquityHTTP:
    def __init__(self, settings: Settings, refresh=False, client: httpx.Client | None = None):
        self.settings, self.refresh = settings, refresh
        self.client = client or httpx.Client(timeout=25, follow_redirects=False)
        self.owns_client = client is None
        self.last_request = 0.0
        self.paused_hosts: set[str] = set()

    def close(self):
        if self.owns_client:
            self.client.close()

    def request(self, url: str, body: dict | None = None) -> bytes:
        if not safe_url(url):
            raise ValueError("İzin verilmeyen kaynak adresi.")
        key = digest(json.dumps([url, body], sort_keys=True).encode())
        pointer = self.settings.data_dir / "equity-cache" / "http" / f"{key}.json"
        if not self.refresh and pointer.is_file():
            meta = json.loads(pointer.read_text())
            sha = meta.get("sha256", "")
            if re.fullmatch(r"[0-9a-f]{64}", sha):
                cached = self.settings.data_dir / "raw" / sha
                if cached.is_file() and cached.stat().st_size <= self.settings.max_download_bytes:
                    raw = cached.read_bytes()
                    if digest(raw) == sha:
                        return raw
        host = urlsplit(url).hostname
        if host in self.paused_hosts:
            raise ValueError("Kaynak bağlantısı bu koşuda duraklatıldı; önbellek korunuyor.")
        time.sleep(max(0, 2.0 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        # No anti-bot bypass, TLS disabling, credentials or uncontrolled redirects.
        with self.client.stream(
            "POST" if body is not None else "GET",
            url,
            **({"json": body} if body is not None else {}),
            headers={"User-Agent": "BilancoResearch/0.2", "Referer": KAP + "/tr/bildirim-sorgu"},
        ) as response:
            if response.status_code == 429:
                self.paused_hosts.add(host)
                raise ValueError(
                    "HTTP 429; bu sunucuya yeni istekler durduruldu. "
                    f"Retry-After: {response.headers.get('retry-after', 'belirtilmedi')}"
                )
            if response.status_code != 200:
                raise ValueError(f"HTTP {response.status_code}; kaynak alınamadı.")
            chunks, size = [], 0
            for part in response.iter_bytes():
                size += len(part)
                if size > self.settings.max_download_bytes:
                    raise ValueError("İndirme boyut sınırını aşıyor.")
                chunks.append(part)
            raw = b"".join(chunks)
        if not raw:
            raise ValueError("Boş kaynak.")
        sha = digest(raw)
        atomic_write(self.settings.data_dir / "raw" / sha, raw)
        write_json(pointer, {"sha256": sha, "retrieved_at": datetime.now(UTC).isoformat()})
        return raw


@dataclass
class Dataset:
    sources: list[EquitySource] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)
    market: list[MarketSeries] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def document_blocks(raw: bytes, source_id: str) -> tuple[list[Block], list[str]]:
    if not raw.startswith(b"%PDF-"):
        raise ValueError("Özgün KAP PDF dosyası bekleniyor; HTML hata sayfası kabul edilmedi.")
    source = Source(
        id=source_id,
        url=KAP,
        sha256=digest(raw),
        media_type="application/pdf",
        retrieved_at=datetime.now(UTC),
        path="",
        publication_date=date(2000, 1, 1),
        publication_proof="pending",
        provenance="dated_official",
        version_note="pending",
    )
    return read_document(source, raw)


def accept_kap(
    raw: bytes, disclosure_id: int, company: Company, as_of: date, settings: Settings, manual=False
) -> tuple[EquitySource, list[Block], list[str]]:
    sha = digest(raw)
    sid = f"kap-{disclosure_id}-{sha[:16]}"
    blocks, issues = document_blocks(raw, sid)
    text = "\n".join(b.text for b in blocks)
    head = text[:5000]
    if company.identity not in fold(head):
        raise ValueError("KAP bildiriminde şirket kimliği eşleşmedi.")
    if not re.search(
        rf"https?://(?:www\.)?kap\.org\.tr/tr/Bildirim/{disclosure_id}(?!\d)", head, re.I
    ):
        raise ValueError("KAP kalıcı bildirim numarası dosyada kanıtlanmadı.")
    dates = re.findall(
        r"yay[ıi]nlanma tarihi ve saati\s*:\s*(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2})", text, re.I
    )
    if not dates:
        raise ValueError("KAP dosyasında yayımlanma zamanı bulunamadı.")
    times = {public_date(t) for t in dates}
    if len(times) != 1:
        raise ValueError("Birden çok bildirim/sürüm içeren PDF kabul edilmedi.")
    published = times.pop()
    if published > cutoff(as_of):
        raise ValueError("future_publication: kesimden sonra yayımlanmış belge.")
    # Classify the cover's own subject, not references to reports in the body.
    # New-contract disclosures often mention the latest financial report.
    cover_lines = [fold(line) for line in head.splitlines()[:12]]
    kind = "disclosure"
    if any(
        re.fullmatch(r"(?:\d{2}\.\d{2}\.20\d{2} (?:donemi )?)?finansal rapor", line)
        for line in cover_lines
    ):
        kind = "financial"
    elif any(
        re.fullmatch(r"faaliyet raporu(?: konsolide olmayan| konsolide)?", line)
        for line in cover_lines
    ):
        kind = "activity"
    path = settings.data_dir / "raw" / sha
    atomic_write(path, raw)
    source = EquitySource(
        id=sid,
        disclosure_id=disclosure_id,
        url=f"{KAP}/tr/api/BildirimPdf/{disclosure_id}",
        sha256=sha,
        retrieved_at=datetime.now(UTC),
        published_at=published,
        available_at=published,
        publication_proof=f"KAP PDF kapak: {dates[0]}; Bildirim/{disclosure_id}",
        provenance="manual_kap" if manual else "kap_public",
        path=str(path.relative_to(settings.data_dir)),
        kind=kind,
        entity_name=company.name,
        entity_code=company.ticker,
        version_note=(
            "Manuel dosyanın özgün sunucudan indirildiği kriptografik olarak doğrulanamaz. "
            if manual
            else ""
        )
        + "Kalıcı bildirim kimliği ve PDF yayın zamanı doğrulandı; sonradan değiştirilmemiş baytların bağımsız arşiv kanıtı yok.",
    )
    return source, blocks, [f"{sid}: {issue}" for issue in issues]


def accept_spk(
    raw: bytes, url: str, company: Company, as_of: date, settings: Settings, manual=False
) -> tuple[EquitySource, list[Block]]:
    p = urlsplit(url)
    if not safe_url(url) or p.hostname not in {"spk.gov.tr", "www.spk.gov.tr"}:
        raise ValueError("SPK özgün adresi gerekli.")
    sha = digest(raw)
    sid = f"spk-{sha[:24]}"
    blocks, _ = document_blocks(raw, sid)
    text = "\n".join(b.text for b in blocks)
    match = re.search(r"\b(20\d{2})/(\d+)\s+(\d{2}/\d{2}/20\d{2})", text[:3000])
    if not match or not re.search(rf"/{match[1]}-{match[2]}\.pdf$", url):
        raise ValueError("SPK bülten kimliği/yayın tarihi eşleşmedi.")
    day = datetime.strptime(match[3], "%d/%m/%Y").date()
    if available_at(day) > cutoff(as_of):
        raise ValueError("future_publication: SPK bülteni henüz erişilebilir değil.")
    selected = [b for b in blocks if company.identity in fold(b.text) or company.ticker in b.text]
    if not selected:
        raise ValueError("SPK bülteninde ilgili şirket bulunamadı.")
    # The AI gets only the relevant subsection, not other issuers' enforcement cases.
    relevant = []
    for b in selected:
        lines = b.text.splitlines()
        start = next(
            i
            for i, line in enumerate(lines)
            if company.identity in fold(line) or company.ticker in line
        )
        end = next(
            (i for i in range(start + 1, len(lines)) if re.match(r"^[a-zçğıöşü]\)\s", lines[i])),
            len(lines),
        )
        body = "\n".join(lines[start:end])
        relevant.append(
            Block(
                id=digest(body.encode())[:24],
                source_id=sid,
                page=b.page,
                line_start=b.line_start + start,
                text=body,
            )
        )
    path = settings.data_dir / "raw" / sha
    atomic_write(path, raw)
    return EquitySource(
        id=sid,
        disclosure_id=None,
        url=url,
        sha256=sha,
        retrieved_at=datetime.now(UTC),
        published_at=datetime.combine(day, datetime.min.time(), ISTANBUL),
        available_at=available_at(day),
        publication_proof=f"SPK {match[1]}/{match[2]}, {match[3]}; gün kesinliğinde, ertesi gün kullanılabilir.",
        provenance="manual_spk" if manual else "spk_public",
        path=str(path.relative_to(settings.data_dir)),
        kind="regulatory",
        version_note="Tedbir duyurusu; kesinleşmiş suç etiketi değildir.",
    ), relevant


def attachment_metadata(raw: bytes, parent: EquitySource, as_of: date):
    data = json.loads(raw)
    if not isinstance(data, list) or len(data) != 1:
        raise ValueError("KAP ek metadata biçimi eşleşmedi.")
    detail = data[0]
    if not isinstance(detail, dict) or not isinstance(detail.get("disclosure"), dict):
        raise ValueError("KAP ek kaydı bozuk.")
    basic = detail["disclosure"].get("disclosureBasic")
    if not isinstance(basic, dict):
        raise ValueError("KAP bildirim kimlik kaydı bozuk.")
    stamp = public_date(basic["publishDate"])
    if (
        int(basic["disclosureIndex"]) != parent.disclosure_id
        or basic.get("isBlocked")
        or abs((stamp - parent.published_at).total_seconds()) > 60
        or stamp > cutoff(as_of)
    ):
        raise ValueError("KAP ekinin bildirim/sürüm/tarih bağlantısı doğrulanamadı.")
    entries = detail.get("attachments", [])
    if not isinstance(entries, list) or len(entries) > 30:
        raise ValueError("KAP ek sayısı/biçimi sınırı.")
    if any(
        not isinstance(entry, dict) or not {"objId", "fileName", "fileExtension"} <= entry.keys()
        for entry in entries
    ):
        raise ValueError("KAP ek metadata satırı bozuk.")
    return entries


def accept_attachment(raw, entry, parent, company, settings, manual=False):
    oid = str(entry["objId"])
    if (
        not re.fullmatch(r"[0-9a-fA-F]{32}", oid)
        or str(entry.get("fileExtension", "")).lower() != "pdf"
    ):
        raise ValueError("Ek dosya kimliği veya türü desteklenmiyor.")
    # Some KAP responses wrap a primitive Java byte[], NEVER deserialize arbitrary Java.
    if raw.startswith(bytes.fromhex("aced0005757200025b42")):
        if len(raw) < 27 or int.from_bytes(raw[23:27], "big") != len(raw) - 27:
            raise ValueError("KAP byte[] boyutu doğrulanamadı.")
        raw = raw[27:]
    sha = digest(raw)
    sid = f"kap-{parent.disclosure_id}-{oid}-{sha[:12]}"
    blocks, issues = document_blocks(raw, sid)
    if not blocks or sum(len(b.text.strip()) for b in blocks) < 20:
        raise ValueError("attachment_text_unreadable: metin okunamadı; OCR gerekiyor.")
    if company.identity not in fold(" ".join(b.text for b in blocks)):
        raise ValueError("attachment_identity_unverified: Ek dosyada şirket kimliği eşleşmedi.")
    path = settings.data_dir / "raw" / sha
    atomic_write(path, raw)
    source = parent.model_copy(
        update={
            "id": sid,
            "url": f"{KAP}/tr/api/file/download/{oid}",
            "sha256": sha,
            "path": str(path.relative_to(settings.data_dir)),
            "kind": "financial_attachment" if parent.kind == "financial" else "attachment",
            "publication_proof": parent.publication_proof
            + f"; KAP attachment-detail objId={oid}, fileName={entry['fileName']}",
            "provenance": "manual_kap" if manual else "kap_public",
            "version_note": parent.version_note + " Ek, aynı bildirim metadata kaydına bağlandı.",
        }
    )
    return source, blocks, [f"{sid}: {issue}" for issue in issues]


def read_market_csv(raw: bytes, symbol: str, url: str, basis: str, as_of: date) -> MarketSeries:
    if urlsplit(url).scheme != "https":
        raise ValueError("Piyasa verisi için HTTPS kaynak adresi gerekli.")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not {"date", "symbol", "close", "volume"} <= set(reader.fieldnames or []):
        raise ValueError("CSV sütunları: date,symbol,close,volume (ISO tarih, noktalı ondalık).")
    bars = {}
    for row in reader:
        day = date.fromisoformat(row["date"])
        if day > as_of:
            continue
        if row["symbol"] != symbol:
            raise ValueError("CSV sembolü eşleşmedi.")
        try:
            bar = PriceBar(
                symbol=symbol,
                day=day,
                close=Decimal(row["close"]),
                volume=Decimal(row["volume"]) if row["volume"] else None,
            )
        except (InvalidOperation, TypeError) as exc:
            raise ValueError("Piyasa CSV tutarı okunamadı.") from exc
        if day in bars and bars[day] != bar:
            raise ValueError("Aynı gün için çelişen piyasa kayıtları.")
        bars[day] = bar
    # Only admitted rows are fingerprinted; appended future data cannot alter a snapshot.
    rows = sorted(bars.values(), key=lambda b: b.day)
    return MarketSeries(
        symbol=symbol,
        url=url,
        retrieved_at=datetime.now(UTC),
        sha256=digest("\n".join(b.model_dump_json() for b in rows).encode()),
        price_basis=basis,
        bars=rows,
        limitations=[
            "Manuel piyasa dosyasının kaynak/sürüm beyanı bağımsız sunucu doğrulaması değildir."
        ],
    )


def yahoo_series(http: EquityHTTP, symbol: str, as_of: date) -> MarketSeries:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1d"
    raw = http.request(url)
    data = json.loads(raw)["chart"]
    if not isinstance(data, dict):
        raise ValueError("Yahoo chart biçimi bozuk.")
    if data.get("error") or not data.get("result"):
        raise ValueError("Yahoo piyasa verisi bulunamadı.")
    row = data["result"][0]
    if not isinstance(row, dict) or not isinstance(row.get("meta"), dict):
        raise ValueError("Yahoo seri metadata biçimi bozuk.")
    if row["meta"]["symbol"] != symbol or row["meta"].get("currency") != "TRY":
        raise ValueError("Piyasa kimliği/para birimi eşleşmedi.")
    times, quote = row["timestamp"], row["indicators"]["quote"][0]
    if len(quote["close"]) != len(times) or len(quote["volume"]) != len(times):
        raise ValueError("Piyasa sütun uzunlukları eşleşmedi.")
    bars = []
    for stamp, closing, volume in zip(times, quote["close"], quote["volume"], strict=True):
        day = datetime.fromtimestamp(stamp, UTC).astimezone(ISTANBUL).date()
        if day <= as_of and closing is not None:
            bars.append(
                PriceBar(
                    symbol=symbol,
                    day=day,
                    close=Decimal(str(closing)),
                    volume=Decimal(str(volume)) if volume is not None else None,
                )
            )
    if len({b.day for b in bars}) != len(bars):
        raise ValueError("Tekrarlanan piyasa günü.")
    bars.sort(key=lambda b: b.day)
    return MarketSeries(
        symbol=symbol,
        url=url,
        retrieved_at=datetime.now(UTC),
        sha256=digest("\n".join(b.model_dump_json() for b in bars).encode()),
        price_basis="provider_adjusted",
        bars=bars,
        limitations=[
            "Deneysel, sözleşmeli API olmayan Yahoo bağlantısı; bugünden yeniden oluşturulan fiyat geçmişi.",
            "Fiyat düzeltmelerinin geçmiş sürümü kanıtlanmadı; nominal piyasa değeri/çarpan hesaplanmadı.",
        ],
    )


def resolve_member(client: EquityHTTP, company: Company) -> str:
    """Resolve an issuer route without treating current metadata as historical evidence."""
    if company.kap_member:
        return company.kap_member
    if company.identity_disclosure_id is None:
        raise ValueError("KAP üye kimliği veya kimlik referansı eksik.")
    payload = json.loads(
        client.request(
            f"{KAP}/tr/api/notification/attachment-detail/{company.identity_disclosure_id}"
        )
    )
    if not isinstance(payload, list) or len(payload) != 1:
        raise ValueError("KAP kimlik kaydı biçimi doğrulanamadı.")
    try:
        basic = payload[0]["disclosure"]["disclosureBasic"]
        member = basic["mkkMemberOid"]
        if (
            int(basic["disclosureIndex"]) != company.identity_disclosure_id
            or company.identity not in fold(basic["companyTitle"])
            or company.ticker not in re.split(r"[^A-Z0-9]+", basic["stockCode"])
            or not re.fullmatch(r"[0-9a-fA-F]{32}", member)
        ):
            raise ValueError("KAP şirket/üye kimliği eşleşmedi.")
    except (KeyError, TypeError) as exc:
        raise ValueError("KAP kimlik alanları okunamadı.") from exc
    return member


def acquire(
    settings: Settings,
    company: Company,
    as_of: date,
    *,
    bundle: Path | None = None,
    refresh=False,
    http: EquityHTTP | None = None,
    progress=lambda _: None,
    offline=False,
) -> Dataset:
    result = Dataset()
    if offline and not bundle:
        raise ValueError("Çevrimdışı inceleme için --bundle gerekli.")
    client = http or EquityHTTP(settings, refresh)
    supplied_market = set()

    def add(raw, index, manual=False, *, entity=company, role="issuer"):
        try:
            source, blocks, issues = accept_kap(raw, index, entity, as_of, settings, manual)
            if role == "related_fund":
                source = source.model_copy(update={"role": role, "kind": "fund_disclosure"})
            if source.sha256 not in {s.sha256 for s in result.sources}:
                result.sources.append(source)
                result.blocks.extend(blocks)
                result.issues.extend(issues)
            return source
        except ValueError as exc:
            result.rejected.append({"disclosure_id": index, "reason": str(exc)})
            return None

    def add_attachment(get_raw, entry, parent, manual=False, *, entity=company):
        oid = str(entry.get("objId", ""))
        try:
            source, blocks, issues = accept_attachment(
                get_raw(), entry, parent, entity, settings, manual
            )
            if parent.role == "related_fund":
                source = source.model_copy(update={"kind": "fund_attachment"})
            if source.sha256 not in {s.sha256 for s in result.sources}:
                result.sources.append(source)
                result.blocks.extend(blocks)
                result.issues.extend(issues)
        except (ValueError, KeyError, TypeError, httpx.HTTPError) as exc:
            # A rejected exhibit must not skip the remaining siblings.
            result.rejected.append(
                {
                    "stage": "attachment",
                    "source_id": parent.id,
                    "disclosure_id": parent.disclosure_id,
                    "obj_id": oid,
                    "reason": str(exc)[:300] if isinstance(exc, ValueError) else type(exc).__name__,
                }
            )
            result.issues.append(
                f"KAP {parent.disclosure_id} ek {oid} alınamadı ({type(exc).__name__})."
            )

    try:
        if bundle:
            manifest = Bundle.model_validate_json(local_file(bundle, "manifest.json", 1_000_000))
            if manifest.company != company.id:
                raise ValueError("Paket şirketi eşleşmedi.")
            for entry in manifest.documents:
                parent = add(
                    local_file(bundle, entry.file, settings.max_download_bytes),
                    entry.disclosure_id,
                    True,
                )
                if parent and entry.attachments:
                    if not entry.detail_file:
                        raise ValueError(
                            "Manuel ek için KAP attachment-detail JSON kanıtı gerekli."
                        )
                    metadata = attachment_metadata(
                        local_file(bundle, entry.detail_file, 2_000_000), parent, as_of
                    )
                    by_id = {str(a.get("objId")): a for a in metadata}
                    for oid, filename in entry.attachments.items():
                        if oid not in by_id or Path(filename).name != by_id[oid]["fileName"]:
                            raise ValueError(
                                "Manuel ekin KAP metadata dosya adı/kimliği eşleşmedi."
                            )
                        add_attachment(
                            lambda filename=filename: local_file(
                                bundle, filename, settings.max_download_bytes
                            ),
                            by_id[oid],
                            parent,
                            True,
                        )
            for entry in manifest.related_documents:
                try:
                    # A supplied routing entry is not evidence of a relationship.
                    # Both fund code and exact name must occur in a primary source span.
                    issuer_ids = {s.id for s in result.sources if s.role == "issuer"}
                    if not any(
                        b.source_id in issuer_ids
                        and fold(entry.fund_name) in fold(b.text)
                        and re.search(r"(?<!\w)" + re.escape(entry.fund_code) + r"(?!\w)", b.text)
                        for b in result.blocks
                    ):
                        raise ValueError(
                            "related_fund_link_unverified: fon kodu/adı şirket belgesinde birlikte doğrulanmadı."
                        )
                    entity = Company(
                        id=entry.fund_code.lower(),
                        name=entry.fund_name,
                        identity=fold(entry.fund_name),
                        ticker=entry.fund_code,
                        listed_at=date(1900, 1, 1),
                    )
                    if offline and not entry.file:
                        raise ValueError("related_fund_offline_file_required")
                    raw = (
                        local_file(bundle, entry.file, settings.max_download_bytes)
                        if entry.file
                        else client.request(f"{KAP}/tr/api/BildirimPdf/{entry.disclosure_id}")
                    )
                    parent = add(
                        raw,
                        entry.disclosure_id,
                        bool(entry.file),
                        entity=entity,
                        role="related_fund",
                    )
                    if parent and entry.attachments:
                        if not entry.detail_file:
                            raise ValueError(
                                "İlişkili fon eki için KAP attachment-detail kanıtı gerekli."
                            )
                        metadata = attachment_metadata(
                            local_file(bundle, entry.detail_file, 2_000_000), parent, as_of
                        )
                        by_id = {str(a.get("objId")): a for a in metadata}
                        for oid, filename in entry.attachments.items():
                            if oid not in by_id or Path(filename).name != by_id[oid]["fileName"]:
                                raise ValueError(
                                    "İlişkili fon eki metadata kimliği/dosya adı eşleşmedi."
                                )
                            add_attachment(
                                lambda filename=filename: local_file(
                                    bundle, filename, settings.max_download_bytes
                                ),
                                by_id[oid],
                                parent,
                                True,
                                entity=entity,
                            )
                except (ValueError, OSError, httpx.HTTPError) as exc:
                    result.rejected.append(
                        {
                            "stage": "related_fund",
                            "disclosure_id": entry.disclosure_id,
                            "fund_code": entry.fund_code,
                            "reason": str(exc)[:300],
                        }
                    )
            for entry in manifest.bulletins:
                try:
                    source, blocks = accept_spk(
                        local_file(bundle, entry.file, settings.max_download_bytes),
                        entry.url,
                        company,
                        as_of,
                        settings,
                        True,
                    )
                    result.sources.append(source)
                    result.blocks.extend(blocks)
                except ValueError as exc:
                    result.rejected.append({"url": entry.url, "reason": str(exc)})
            for entry in manifest.market:
                if (
                    entry.symbol not in {company.ticker + ".IS", "XU100.IS"}
                    or entry.symbol in supplied_market
                ):
                    raise ValueError("Paket piyasa sembolü bilinmiyor veya tekrarlanmış.")
                result.market.append(
                    read_market_csv(
                        local_file(bundle, entry.file, settings.max_download_bytes),
                        entry.symbol,
                        entry.url,
                        entry.price_basis,
                        as_of,
                    )
                )
                supplied_market.add(entry.symbol)
        else:
            # Website endpoint is experimental, not the licensed production REST API.
            ids = set()
            ordering = {}
            start = max(
                date(company.listed_at.year, 1, 1),
                as_of - timedelta(days=company.catalog_lookback_days),
            )
            if start > date(company.listed_at.year, 1, 1):
                result.issues.append(
                    f"KAP katalog penceresi {start}–{as_of}; daha eski açıklamalar taranmadı."
                )
            try:
                member = resolve_member(client, company)
                while start <= as_of:
                    end = min(start + timedelta(days=89), as_of)
                    progress(f"KAP katalog {start}–{end}")
                    rows = json.loads(
                        client.request(
                            KAP + "/tr/api/disclosure/members/byCriteria",
                            {
                                "fromDate": start.isoformat(),
                                "toDate": end.isoformat(),
                                "mkkMemberOidList": [member],
                                "subjectList": [],
                            },
                        )
                    )
                    if not isinstance(rows, list) or len(rows) >= 2000:
                        raise ValueError("KAP katalog biçimi/kapsam sınırı; tamlık kanıtlanamadı.")
                    for row in rows:
                        if not isinstance(row, dict):
                            raise ValueError("KAP katalog satırı bozuk.")
                        symbols = (
                            str(row.get("stockCodes", "")) + "," + str(row.get("relatedStocks", ""))
                        )
                        if company.ticker not in re.split(r"[^A-Z0-9]+", symbols):
                            continue
                        published = public_date(row["publishDate"])
                        subject = fold(str(row.get("subject", "")))
                        if (
                            published <= cutoff(as_of)
                            and "devre kesici" not in subject
                            and "sorumluluk beyani" not in subject
                        ):
                            index = int(row["disclosureIndex"])
                            ids.add(index)
                            tier = (
                                0
                                if subject == "finansal rapor"
                                else 1
                                if "faaliyet raporu" in subject
                                else 2
                            )
                            ordering[index] = (tier, -published.timestamp(), index)
                    start = end + timedelta(days=1)
            except (ValueError, KeyError, TypeError, httpx.HTTPError) as exc:
                result.issues.append(
                    f"KAP katalog alınamadı ({type(exc).__name__}); belge paketi kullanılabilir."
                )
                # URL-only seeds, never preloaded financial values or publication dates.
                if company.id == "ozatd":
                    ids.update((1399375, 1399372, 1475464))
            if len(ids) > 400:
                result.issues.append("400 bildirim sınırı aşıldı; tam kapsam yok.")
            ordered_ids = sorted(ids, key=lambda i: ordering.get(i, (3, 0, -i)))
            for index in ordered_ids[:400]:
                progress(f"KAP PDF {index}")
                try:
                    parent = add(client.request(f"{KAP}/tr/api/BildirimPdf/{index}"), index)
                    if parent:
                        try:
                            metadata = attachment_metadata(
                                client.request(
                                    f"{KAP}/tr/api/notification/attachment-detail/{index}"
                                ),
                                parent,
                                as_of,
                            )
                            for entry in metadata:
                                oid = str(entry.get("objId", ""))
                                if (
                                    not re.fullmatch(r"[0-9a-fA-F]{32}", oid)
                                    or str(entry.get("fileExtension", "")).lower() != "pdf"
                                ):
                                    continue
                                add_attachment(
                                    lambda oid=oid: client.request(
                                        f"{KAP}/tr/api/file/download/{oid}"
                                    ),
                                    entry,
                                    parent,
                                )
                        except (ValueError, KeyError, TypeError, httpx.HTTPError) as exc:
                            result.issues.append(
                                f"KAP {index} ek kapsamı alınamadı ({type(exc).__name__})."
                            )
                            result.rejected.append(
                                {
                                    "stage": "attachment_metadata",
                                    "source_id": parent.id,
                                    "disclosure_id": index,
                                    "reason": str(exc)[:300]
                                    if isinstance(exc, ValueError)
                                    else type(exc).__name__,
                                }
                            )
                except (ValueError, httpx.HTTPError) as exc:
                    result.rejected.append(
                        {"disclosure_id": index, "reason": f"download_failed:{type(exc).__name__}"}
                    )
            if company.id == "ozatd" and available_at(date(2025, 4, 30)) <= cutoff(as_of):
                try:
                    source, blocks = accept_spk(
                        client.request(SPK_2025), SPK_2025, company, as_of, settings
                    )
                    result.sources.append(source)
                    result.blocks.extend(blocks)
                except (ValueError, httpx.HTTPError) as exc:
                    result.issues.append(f"SPK bülteni alınamadı ({type(exc).__name__}).")
        for symbol in (company.ticker + ".IS", "XU100.IS"):
            if symbol in supplied_market:
                continue
            if offline:
                result.issues.append(f"{symbol} çevrimdışı pakette bulunamadı.")
                continue
            try:
                progress(f"Piyasa verisi {symbol}")
                result.market.append(yahoo_series(client, symbol, as_of))
            except (ValueError, KeyError, TypeError, httpx.HTTPError) as exc:
                result.issues.append(
                    f"{symbol} fiyat/hacim alınamadı ({type(exc).__name__}); CSV aktarımı kullanılabilir."
                )
    finally:
        if http is None:
            client.close()
    return result
