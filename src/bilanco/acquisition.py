import re
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from .config import (
    ACCESSION,
    CIK,
    FILING_URL,
    INDEX_URL,
    MIRROR_URLS,
    PERIOD,
    SUBMISSIONS_URL,
    Settings,
)
from .models import Source
from .storage import Store, atomic_write, digest

ALLOWED_HOSTS = frozenset(
    {
        "www.sec.gov",
        "sec.gov",
        "data.sec.gov",
        "picker.uchicago.edu",
        "enroncorp.com",
        "www.enroncorp.com",
    }
)


class AcquisitionError(Exception):
    pass


def allowed_url(url: str) -> bool:
    if len(url) > 4096:
        return False
    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname in ALLOWED_HOSTS
            and parsed.port in (None, 443)
            and not parsed.username
            and not parsed.password
            and not parsed.fragment
            and not any(ord(c) < 33 for c in url)
        )
    except ValueError:
        return False


@dataclass
class Download:
    requested_url: str
    url: str
    content: bytes
    sha256: str
    media_type: str
    retrieved_at: datetime
    path: str
    cached: bool


class Acquirer:
    def __init__(
        self,
        settings: Settings,
        store: Store,
        refresh: bool = False,
        client: httpx.Client | None = None,
    ):
        self.settings, self.store, self.refresh = settings, store, refresh
        self.client = client or httpx.Client(timeout=45, follow_redirects=False)
        self._owns_client = client is None
        self._last_request = 0.0
        self.request_seconds = 0.0

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def get(self, url: str) -> Download:
        if not allowed_url(url):
            raise AcquisitionError("Kaynak izin verilen HTTPS alan adlarından değil.")
        cached = None if self.refresh else self.store.cached_download(url)
        if cached:
            expected = cached.get("sha256", "")
            # Never trust a DB-supplied path; derive it from a validated digest.
            if re.fullmatch(r"[0-9a-f]{64}", expected):
                path = self.settings.data_dir / "raw" / expected
                if path.is_file() and path.stat().st_size <= self.settings.max_download_bytes:
                    content = path.read_bytes()
                    if digest(content) == expected and allowed_url(cached.get("url", "")):
                        return Download(
                            url,
                            cached["url"],
                            content,
                            expected,
                            cached["media_type"],
                            datetime.fromisoformat(cached["retrieved_at"]),
                            str(path.relative_to(self.settings.data_dir)),
                            True,
                        )
        current = url
        for _ in range(6):
            if not allowed_url(current):
                raise AcquisitionError("Yönlendirme izin verilen alan adlarından çıktı.")
            wait = 0.25 - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()
            request_start = time.perf_counter()
            try:
                response = self._request(current)
            except httpx.HTTPError as exc:
                raise AcquisitionError(f"Kaynağa erişilemedi ({type(exc).__name__}).") from exc
            finally:
                self.request_seconds += time.perf_counter() - request_start
            if response.status_code in (301, 302, 303, 307, 308):
                current = urljoin(current, response.headers.get("location", ""))
                continue
            if response.status_code != 200:
                raise AcquisitionError(f"HTTP {response.status_code}: kaynak alınamadı.")
            content = response.content
            if not content:
                raise AcquisitionError("Boş belge alındı.")
            sha = digest(content)
            path = self.settings.data_dir / "raw" / sha
            atomic_write(path, content)
            now = datetime.now(UTC)
            media = response.headers.get("content-type", "application/octet-stream").split(";")[0]
            metadata = {
                "url": current,
                "sha256": sha,
                "media_type": media,
                "retrieved_at": now.isoformat(),
                "http_status": 200,
            }
            self.store.save_download(url, metadata)
            return Download(
                url,
                current,
                content,
                sha,
                media,
                now,
                str(path.relative_to(self.settings.data_dir)),
                False,
            )
        raise AcquisitionError("Çok fazla yönlendirme.")

    def _request(self, url: str) -> httpx.Response:
        # SEC's identity header contains only the user-provided contact, never login tokens.
        headers = {
            "User-Agent": f"BilancoResearch/0.1 {self.settings.sec_contact}",
            "Accept-Encoding": "gzip, deflate",
        }
        for attempt in range(3):
            with self.client.stream("GET", url, headers=headers) as response:
                length = response.headers.get("content-length", "")
                if length.isdigit() and int(length) > self.settings.max_download_bytes:
                    raise AcquisitionError("Belge boyut sınırını aşıyor.")
                parts, size = [], 0
                for part in response.iter_bytes():
                    size += len(part)
                    if size > self.settings.max_download_bytes:
                        raise AcquisitionError("Belge boyut sınırını aşıyor.")
                    parts.append(part)
                result = httpx.Response(
                    response.status_code,
                    headers=response.headers,
                    content=b"".join(parts),
                    request=response.request,
                )
            if result.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                return result
            delay = result.headers.get("retry-after", "")
            time.sleep(min(int(delay), 10) if delay.isdigit() else 0.5 * (2**attempt))
        raise AssertionError("unreachable")


@dataclass(frozen=True)
class PublicationProof:
    published: date
    description: str


def decode_text(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("cp1252", errors="replace")


def sgml_proof(download: Download, as_of: date, annual: bool = True) -> PublicationProof:
    if urlsplit(download.url).hostname not in {"www.sec.gov", "sec.gov"}:
        raise AcquisitionError("SEC başlığı, resmî SEC alan adından gelmiyor.")
    text = decode_text(download.content)
    header = text[:25_000]

    def field(pattern: str) -> str:
        match = re.search(pattern, header, re.I)
        if not match:
            raise AcquisitionError("Özgün SEC başlığı doğrulanamadı.")
        return match[1].strip()

    cik = field(r"CENTRAL INDEX KEY:\s*(\d+)")
    form = field(r"CONFORMED SUBMISSION TYPE:\s*([^\r\n]+)")
    if int(cik) != int(CIK) or form not in ({"10-K"} if annual else {"8-K", "10-Q"}):
        raise AcquisitionError("Şirket veya özgün dosyalama türü eşleşmiyor.")
    filed = date.fromisoformat(
        datetime.strptime(field(r"FILED AS OF DATE:\s*(\d{8})"), "%Y%m%d").date().isoformat()
    )
    dates = [filed]
    envelope = re.search(r"<SEC-DOCUMENT>[^\r\n]*?\s(\d{8})", header)
    if envelope:
        dates.append(datetime.strptime(envelope[1], "%Y%m%d").date())
    if annual:
        accession = field(r"ACCESSION NUMBER:\s*([^\r\n]+)")
        period = datetime.strptime(field(r"CONFORMED PERIOD OF REPORT:\s*(\d{8})"), "%Y%m%d").date()
        if accession != ACCESSION or period != PERIOD:
            raise AcquisitionError("Beklenen özgün yıllık dosyalama eşleşmiyor.")
    published = max(dates)
    if published > as_of:
        raise AcquisitionError("Belge kesim tarihinden sonra yayımlanmış.")
    return PublicationProof(published, f"SEC SGML header; {download.url}; sha256={download.sha256}")


def index_proof(download: Download, as_of: date) -> PublicationProof:
    if urlsplit(download.url).hostname not in {"www.sec.gov", "sec.gov"}:
        raise AcquisitionError("Dosyalama indeksi resmî SEC alan adından gelmiyor.")
    text = BeautifulSoup(decode_text(download.content), "html.parser").get_text(" ", strip=True)
    if ACCESSION not in text or not re.search(r"\b10-K\b", text) or "1024401" not in text:
        raise AcquisitionError("SEC indeks kimliği doğrulanamadı.")
    match = re.search(r"Filing Date\s+(\d{4}-\d{2}-\d{2})", text, re.I)
    period = re.search(r"Period of Report\s+(\d{4}-\d{2}-\d{2})", text, re.I)
    if not match or not period or date.fromisoformat(period[1]) != PERIOD:
        raise AcquisitionError("SEC indeks yayın/dönem bilgisi doğrulanamadı.")
    published = date.fromisoformat(match[1])
    if published > as_of:
        raise AcquisitionError("SEC indeks tarihi kesimden sonra.")
    return PublicationProof(
        published, f"SEC filing index; {download.url}; sha256={download.sha256}"
    )


def submissions_proof(acquirer: Acquirer, as_of: date) -> PublicationProof:
    import json

    root = acquirer.get(SUBMISSIONS_URL)
    if urlsplit(root.url).hostname != "data.sec.gov":
        raise AcquisitionError("SEC geçmiş metadatasının kaynak alan adı eşleşmiyor.")
    try:
        data = json.loads(root.content)
        if int(data["cik"]) != int(CIK):
            raise AcquisitionError("SEC şirket kimliği eşleşmiyor.")

        def locate(rows: dict, download: Download) -> PublicationProof | None:
            for i, accession in enumerate(rows.get("accessionNumber", [])):
                if accession != ACCESSION:
                    continue
                if rows["form"][i] != "10-K" or rows["reportDate"][i] != PERIOD.isoformat():
                    raise AcquisitionError("SEC dosyalama sürümü eşleşmiyor.")
                published = date.fromisoformat(rows["filingDate"][i])
                if published > as_of:
                    raise AcquisitionError("Dosyalama kesimden sonra.")
                return PublicationProof(
                    published,
                    f"SEC submissions {accession}; {download.url}; sha256={download.sha256}",
                )
            return None

        proof = locate(data["filings"]["recent"], root)
        if proof:
            return proof
        # Historic arrays can be in additional SEC-supplied files. Do not fetch
        # history at all when the target is already in the recent array.
        for item in data["filings"].get("files", [])[:10]:
            name = item.get("name", "")
            if not re.fullmatch(r"CIK0001024401-submissions-\d+\.json", name):
                continue
            try:
                extra = acquirer.get("https://data.sec.gov/submissions/" + name)
            except AcquisitionError:
                continue
            if urlsplit(extra.url).hostname != "data.sec.gov":
                raise AcquisitionError("SEC geçmiş dosyasının kaynak alan adı eşleşmiyor.")
            proof = locate(json.loads(extra.content), extra)
            if proof:
                return proof
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise AcquisitionError("SEC geçmiş dosyalama metadatası okunamadı.") from exc
    raise AcquisitionError("Özgün dosyalama SEC geçmişinde bulunamadı.")


def make_source(download: Download, proof: PublicationProof, provenance: str) -> Source:
    source_id = digest((download.url + "\n" + download.sha256).encode())
    return Source(
        id=source_id,
        url=download.url,
        sha256=download.sha256,
        media_type=download.media_type,
        retrieved_at=download.retrieved_at,
        path=download.path,
        publication_date=proof.published,
        publication_proof=proof.description,
        provenance=provenance,
        cached=download.cached,
        version_note=(
            "Özgün SEC dosyalaması."
            if provenance != "archive_copy"
            else "Arşiv kopyası; yayın tarihi SEC dosyalama kaydıyla ilişkilendirildi. "
            "Özgün SEC dosyasıyla byte eşitliği doğrulanmadı."
        ),
    )


def acquire_annual(
    acquirer: Acquirer,
    as_of: date,
    problems: list[str],
    proof_override: PublicationProof | None = None,
) -> tuple[Source, bytes] | None:
    try:
        original = acquirer.get(FILING_URL)
        proof = sgml_proof(original, as_of)
        return make_source(original, proof, "sec_original"), original.content
    except AcquisitionError as exc:
        problems.append(f"Özgün SEC raporu: {exc}")
    proof = proof_override
    if proof is not None and proof.published > as_of:
        problems.append("Ek yayın kanıtı kesimden sonra; kabul edilmedi.")
        return None
    if proof is None:
        try:
            proof = index_proof(acquirer.get(INDEX_URL), as_of)
        except AcquisitionError as exc:
            problems.append(f"SEC indeks: {exc}")
    if proof is None:
        try:
            proof = submissions_proof(acquirer, as_of)
        except AcquisitionError as exc:
            problems.append(f"SEC geçmişi: {exc}")
    if proof is None:
        problems.append("Yayın tarihi doğrulanamadığı için arşiv PDF'leri analize alınmadı.")
        return None
    for url in MIRROR_URLS:
        try:
            download = acquirer.get(url)
            if not download.content.startswith(b"%PDF-"):
                raise AcquisitionError("Arşiv kopyası PDF değil.")
            return make_source(download, proof, "archive_copy"), download.content
        except AcquisitionError as exc:
            problems.append(f"Arşiv kopyası: {exc}")
    return None
