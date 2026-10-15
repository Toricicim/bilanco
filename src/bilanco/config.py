import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import dotenv_values

AS_OF = date(2000, 3, 31)
CIK = "0001024401"
ACCESSION = "0001024401-00-000002"
PERIOD = date(1999, 12, 31)
SEC_ROOT = "https://www.sec.gov/Archives/edgar/data/1024401"
FILING_URL = f"{SEC_ROOT}/000102440100000002/{ACCESSION}.txt"
INDEX_URL = f"{SEC_ROOT}/{ACCESSION}-index.html"
SUBMISSIONS_URL = f"https://data.sec.gov/submissions/CIK{CIK}.json"
MIRROR_URLS = (
    "https://picker.uchicago.edu/Enron/EnronAnnualReport1999.pdf",
    "https://enroncorp.com/src/doc/investors/1999_Annual_Report.pdf",
)


@dataclass(frozen=True)
class Settings:
    database_url: str = "postgresql:///bilanco"
    data_dir: Path = Path("data")
    sec_contact: str = ""
    codex_model: str = ""
    codex_binary: str = "codex"
    codex_timeout: int = 240
    max_ai_calls: int = 32
    max_download_bytes: int = 25_000_000
    chunk_chars: int = 24_000

    @classmethod
    def load(cls) -> "Settings":
        # Only this directory's .env. Never search parent/home directories.
        env = {**dotenv_values(Path.cwd() / ".env"), **os.environ}
        result = cls(
            database_url=env.get("BILANCO_DATABASE_URL", cls.database_url),
            data_dir=Path(env.get("BILANCO_DATA_DIR", "data")).resolve(),
            sec_contact=env.get("BILANCO_SEC_CONTACT", "").strip(),
            codex_model=env.get("BILANCO_CODEX_MODEL", "").strip(),
            codex_binary=env.get("BILANCO_CODEX_BINARY", "codex"),
            codex_timeout=int(env.get("BILANCO_CODEX_TIMEOUT", "240")),
            max_ai_calls=int(env.get("BILANCO_MAX_AI_CALLS", "32")),
        )
        if result.codex_timeout < 1 or not 1 <= result.max_ai_calls <= 128:
            raise ValueError("Codex timeout pozitif, çağrı sınırı 1–128 olmalı.")
        return result
