import gzip
import io
import zlib
from dataclasses import replace

import httpx
import pytest
from conftest import synthetic_filing
from reportlab.pdfgen.canvas import Canvas

from bilanco.acquisition import (
    Acquirer,
    AcquisitionError,
    acquire_annual,
    allowed_url,
    sgml_proof,
    submissions_proof,
)
from bilanco.config import AS_OF, FILING_URL, INDEX_URL, MIRROR_URLS, SUBMISSIONS_URL
from bilanco.documents import archive_identity_ok, read_document


@pytest.mark.parametrize(
    "url",
    [
        "http://www.sec.gov/test",
        "https://www.sec.gov.evil.test/test",
        "https://127.0.0.1/test",
        "https://www.sec.gov:1234/test",
        "https://user:password@www.sec.gov/test",
        "file:///etc/passwd",
        "https://www.sec.gov/test#fragment",
        "https://www.sec.gov/\nfoo",
    ],
)
def test_disallowed_sources(url):
    assert not allowed_url(url)


def test_only_execution_downloads_and_second_run_reuses_cache(acquirer, settings):
    assert not settings.data_dir.exists()
    first = acquirer.get(FILING_URL)
    second = acquirer.get(FILING_URL)
    assert not first.cached and second.cached
    assert first.sha256 == second.sha256
    assert len(list((settings.data_dir / "raw").iterdir())) == 1


def test_tampered_cache_is_redownloaded(acquirer, settings):
    original = acquirer.get(FILING_URL)
    (settings.data_dir / original.path).write_bytes(b"tampered")
    again = acquirer.get(FILING_URL)
    assert not again.cached
    assert again.content == original.content


def test_refresh_bypasses_cache(acquirer):
    acquirer.get(FILING_URL)
    acquirer.refresh = True
    assert not acquirer.get(FILING_URL).cached


def test_date_not_taken_from_filename_or_fetch_time(acquirer):
    download = acquirer.get(FILING_URL)
    proof = sgml_proof(download, AS_OF)
    assert proof.published.isoformat() == "2000-03-30"
    later = replace(download, content=synthetic_filing(published="20010401"))
    with pytest.raises(AcquisitionError, match="kesim"):
        sgml_proof(later, AS_OF)


@pytest.mark.parametrize(
    "old,new",
    [(b"10-K\n", b"10-K/A\n"), (b"0001024401\n", b"0000821189\n"), (b"19991231", b"20001231")],
)
def test_wrong_form_company_or_period_is_rejected(acquirer, old, new):
    download = acquirer.get(FILING_URL)
    with pytest.raises(AcquisitionError):
        sgml_proof(replace(download, content=download.content.replace(old, new)), AS_OF)


def test_redirect_cannot_escape_allowlist(settings, memory_store):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(302, headers={"location": "https://evil.invalid/stolen"})
    )
    with httpx.Client(transport=transport) as client:
        with pytest.raises(AcquisitionError, match="Yönlendirme"):
            Acquirer(settings, memory_store, client=client).get(FILING_URL)


def test_download_size_limit(settings, memory_store):
    transport = httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * 11))
    with httpx.Client(transport=transport) as client:
        with pytest.raises(AcquisitionError, match="boyut"):
            Acquirer(replace(settings, max_download_bytes=10), memory_store, client=client).get(
                FILING_URL
            )


def test_403_does_not_disable_tls_or_retry_forever(settings, memory_store):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(403)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AcquisitionError, match="403"):
            Acquirer(settings, memory_store, client=client).get(FILING_URL)
    assert len(calls) == 1


@pytest.mark.parametrize("encoding,compress", [("gzip", gzip.compress), ("deflate", zlib.compress)])
def test_compressed_response_is_decoded_once(settings, memory_store, encoding, compress):
    payload = b"SYNTHETIC document body with original bytes retained after HTTP decoding"
    compressed = compress(payload)

    def handler(request):
        return httpx.Response(
            200,
            headers={
                "content-encoding": encoding,
                "content-length": str(len(compressed)),
                "content-type": "text/plain",
            },
            stream=httpx.ByteStream(compressed),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        download = Acquirer(settings, memory_store, client=client).get(FILING_URL)
    assert download.content == payload
    assert (settings.data_dir / download.path).read_bytes() == payload


def test_compressed_error_response_preserves_http_status(settings, memory_store):
    def handler(request):
        return httpx.Response(
            403,
            headers={"content-encoding": "gzip"},
            stream=httpx.ByteStream(gzip.compress(b"SYNTHETIC access denied")),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AcquisitionError, match="HTTP 403"):
            Acquirer(settings, memory_store, client=client).get(FILING_URL)


def test_compressed_payload_still_obeys_decoded_size_limit(settings, memory_store):
    payload = gzip.compress(b"x" * 5000)

    def handler(request):
        return httpx.Response(
            200, headers={"content-encoding": "gzip"}, stream=httpx.ByteStream(payload)
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AcquisitionError, match="boyut"):
            Acquirer(replace(settings, max_download_bytes=100), memory_store, client=client).get(
                FILING_URL
            )


def test_archive_fallback_needs_official_publication_proof(settings, memory_store):
    stream = io.BytesIO()
    canvas = Canvas(stream)
    canvas.drawString(30, 750, "Enron 1999 Annual Report — SYNTHETIC TEST ONLY")
    canvas.drawString(30, 730, "Consolidated Balance Sheets")
    canvas.save()

    def handler(request):
        if str(request.url) == INDEX_URL:
            return httpx.Response(
                200,
                text="<html>0001024401-00-000002 10-K CIK 1024401 Filing Date 2000-03-30 Period of Report 1999-12-31</html>",
            )
        if str(request.url) == MIRROR_URLS[0]:
            return httpx.Response(200, content=stream.getvalue())
        return httpx.Response(403)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = acquire_annual(Acquirer(settings, memory_store, client=client), AS_OF, [])
    assert result is not None
    source, content = result
    assert source.provenance == "archive_copy"
    assert source.publication_date.isoformat() == "2000-03-30"
    blocks, _ = read_document(source, content)
    assert archive_identity_ok(blocks)


def test_unknown_publication_does_not_even_download_mirrors(settings, memory_store):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(403)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert acquire_annual(Acquirer(settings, memory_store, client=client), AS_OF, []) is None
    assert not any(url in MIRROR_URLS for url in calls)


def test_recent_metadata_does_not_fetch_unnecessary_historical_files(settings, memory_store):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(
            200,
            json={
                "cik": "1024401",
                "filings": {
                    "recent": {
                        "accessionNumber": ["0001024401-00-000002"],
                        "form": ["10-K"],
                        "reportDate": ["1999-12-31"],
                        "filingDate": ["2000-03-30"],
                    },
                    "files": [{"name": "CIK0001024401-submissions-001.json"}],
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        proof = submissions_proof(Acquirer(settings, memory_store, client=client), AS_OF)
    assert proof.published <= AS_OF
    assert calls == [SUBMISSIONS_URL]


def test_university_text_cannot_impersonate_official_sec_header(acquirer):
    download = acquirer.get(FILING_URL)
    with pytest.raises(AcquisitionError, match="resmî SEC"):
        sgml_proof(replace(download, url="https://picker.uchicago.edu/forged.txt"), AS_OF)
