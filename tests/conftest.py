import uuid
from datetime import UTC, datetime

import httpx
import pytest

from bilanco.acquisition import Acquirer
from bilanco.config import AS_OF, FILING_URL, Settings
from bilanco.models import Discovery, Extraction, Narrative, Source
from bilanco.storage import digest


def synthetic_filing(
    *,
    published: str = "20000330",
    current: str = "200",
    current_old: str = "150",
    profit: str = "40",
    operating: str = "60",
    years: str = "1999 1998",
    note: bool = True,
) -> bytes:
    # Invented values. Never a historical Enron input or expected Enron result.
    text = f"""<SEC-DOCUMENT>synthetic.txt : {published}
<SEC-HEADER>
ACCESSION NUMBER: 0001024401-00-000002
CONFORMED SUBMISSION TYPE: 10-K
CONFORMED PERIOD OF REPORT: 19991231
FILED AS OF DATE: {published}
FILER:
CENTRAL INDEX KEY: 0001024401
</SEC-HEADER>
<DOCUMENT>
<TYPE>10-K
<TEXT>
SYNTHETIC TEST DATA — NOT HISTORICAL ENRON DATA
CONSOLIDATED BALANCE SHEETS
(In millions of dollars)
{years}
Cash and cash equivalents $30 $20
Total current assets {current} {current_old}
Total current liabilities 100 120
Total assets 500 450
Total liabilities 300 290
Shareholders' equity 200 160
Long-term debt 100 110
CONSOLIDATED STATEMENTS OF INCOME
(In millions of dollars)
1999 1998
Net income {profit} 30
CONSOLIDATED STATEMENTS OF CASH FLOWS
(In millions of dollars)
1999 1998
Net income {profit} 30
Net cash provided by operating activities {operating} 50
NOTES TO CONSOLIDATED FINANCIAL STATEMENTS
"""
    if note:
        text += "A senior officer manages Counterparty A, which purchased an investment.\nManagement believes the terms reflect transactions with unrelated parties.\n"
    return (text + "</TEXT>\n</DOCUMENT>\n").encode()


class MemoryStore:
    def __init__(self):
        self.downloads, self.runs = {}, {}
        self.assessments = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def initialize(self):
        pass

    def cached_download(self, url):
        return self.downloads.get(url)

    def save_download(self, url, metadata):
        self.downloads[url] = metadata

    def start(self, run_id, company, as_of):
        self.runs[run_id] = {"company": company, "as_of": as_of}

    def stage(self, run_id, stage):
        self.runs[run_id]["stage"] = stage

    def finish(self, analysis):
        self.runs[analysis.run_id] = analysis.model_dump(mode="json")

    def load_analysis(self, run_id):
        from bilanco.models import Analysis

        if run_id not in self.runs:
            raise ValueError("Unknown run")
        return Analysis.model_validate(self.runs[run_id])

    def start_assessment(self, assessment):
        self.assessments[assessment.id] = {"status": "running"}

    def finish_assessment(self, assessment):
        self.assessments[assessment.id] = assessment.model_dump(mode="json")


class FakeCodex:
    """A test double, explicitly never described as real model inference."""

    def __init__(self, extraction=None, error=None, discovery=None):
        self.calls = 0
        self.receipts = []
        self.extraction = extraction
        self.error = error
        self.discovery = discovery or Discovery(sources=[])

    def discover(self, missing):
        self.calls += 1
        return self.discovery

    def extract(self, blocks):
        self.calls += 1
        if self.error:
            raise self.error
        return self.extraction or Extraction(candidates=[])

    def order(self, findings):
        self.calls += 1
        return Narrative(items=[])


@pytest.fixture(autouse=True)
def no_real_http(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Real network is forbidden in tests. Use MockTransport.")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "data", sec_contact="test@synthetic.invalid")


@pytest.fixture
def memory_store():
    return MemoryStore()


@pytest.fixture
def transport():
    def handler(request):
        if str(request.url) == FILING_URL:
            return httpx.Response(
                200, content=synthetic_filing(), headers={"content-type": "text/plain"}
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.fixture
def acquirer(settings, memory_store, transport):
    with httpx.Client(transport=transport) as client:
        yield Acquirer(settings, memory_store, client=client)


@pytest.fixture
def source():
    return Source(
        id=str(uuid.uuid4()),
        url=FILING_URL,
        sha256=digest(synthetic_filing()),
        media_type="text/plain",
        retrieved_at=datetime.now(UTC),
        path="raw/synthetic",
        publication_date=AS_OF,
        publication_proof="Synthetic fixture only",
        provenance="sec_original",
        version_note="Synthetic fixture only",
    )
