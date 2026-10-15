import hashlib
import json
import os
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .models import Analysis

DDL = """
CREATE SCHEMA IF NOT EXISTS bilanco;
CREATE TABLE IF NOT EXISTS bilanco.migrations (
    version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS bilanco.downloads (
    url text PRIMARY KEY, sha256 text NOT NULL, metadata jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS bilanco.runs (
    id uuid PRIMARY KEY, company text NOT NULL, as_of date NOT NULL,
    status text NOT NULL, stage text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
    analysis jsonb
);
CREATE TABLE IF NOT EXISTS bilanco.sources (
    id text PRIMARY KEY, sha256 text NOT NULL, metadata jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS bilanco.run_sources (
    run_id uuid REFERENCES bilanco.runs(id), source_id text REFERENCES bilanco.sources(id),
    metadata jsonb NOT NULL, PRIMARY KEY (run_id, source_id)
);
CREATE TABLE IF NOT EXISTS bilanco.blocks (
    run_id uuid REFERENCES bilanco.runs(id), id text NOT NULL,
    source_id text REFERENCES bilanco.sources(id), payload jsonb NOT NULL,
    PRIMARY KEY (run_id, id)
);
CREATE TABLE IF NOT EXISTS bilanco.facts (
    run_id uuid REFERENCES bilanco.runs(id), id text NOT NULL,
    concept text NOT NULL, period integer NOT NULL, value numeric NOT NULL,
    unit text NOT NULL, scale bigint NOT NULL, block_id text NOT NULL,
    payload jsonb NOT NULL, PRIMARY KEY (run_id, id),
    UNIQUE(run_id,concept,period),
    FOREIGN KEY(run_id,block_id) REFERENCES bilanco.blocks(run_id,id)
);
CREATE TABLE IF NOT EXISTS bilanco.metrics (
    run_id uuid REFERENCES bilanco.runs(id), id text NOT NULL,
    period integer NOT NULL, value numeric NOT NULL, payload jsonb NOT NULL,
    PRIMARY KEY (run_id,id)
);
CREATE TABLE IF NOT EXISTS bilanco.findings (
    run_id uuid REFERENCES bilanco.runs(id), id text NOT NULL,
    payload jsonb NOT NULL, PRIMARY KEY (run_id, id)
);
INSERT INTO bilanco.migrations(version) VALUES (1) ON CONFLICT DO NOTHING;
"""


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


class Store:
    def __init__(self, dsn: str):
        self.connection = psycopg.connect(dsn, autocommit=True, connect_timeout=5)

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *_: object) -> None:
        self.connection.close()

    def initialize(self) -> None:
        # Transactional DDL; serialize first-time initialization across processes.
        with self.connection.transaction():
            self.connection.execute("SELECT pg_advisory_xact_lock(742823991)")
            self.connection.execute(DDL)
            version = self.connection.execute(
                "SELECT max(version) FROM bilanco.migrations"
            ).fetchone()[0]
            if version != 1:
                raise RuntimeError("Desteklenmeyen veritabanı şeması")

    def cached_download(self, url: str) -> dict | None:
        row = self.connection.execute(
            "SELECT metadata FROM bilanco.downloads WHERE url = %s", (url,)
        ).fetchone()
        return row[0] if row else None

    def save_download(self, url: str, metadata: dict) -> None:
        self.connection.execute(
            "INSERT INTO bilanco.downloads(url,sha256,metadata) VALUES (%s,%s,%s) "
            "ON CONFLICT (url) DO UPDATE SET sha256=EXCLUDED.sha256, metadata=EXCLUDED.metadata",
            (url, metadata["sha256"], Jsonb(metadata)),
        )

    def start(self, run_id: str, company: str, as_of: object) -> None:
        self.connection.execute(
            "INSERT INTO bilanco.runs(id,company,as_of,status,stage) VALUES (%s,%s,%s,'running','start')",
            (run_id, company, as_of),
        )

    def stage(self, run_id: str, stage: str) -> None:
        self.connection.execute("UPDATE bilanco.runs SET stage=%s WHERE id=%s", (stage, run_id))

    def finish(self, analysis: Analysis) -> None:
        run_id = analysis.run_id
        with self.connection.transaction():
            for source in analysis.sources:
                obj = source.model_dump(mode="json")
                self.connection.execute(
                    "INSERT INTO bilanco.sources VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                    (source.id, source.sha256, Jsonb(obj)),
                )
                self.connection.execute(
                    "INSERT INTO bilanco.run_sources VALUES (%s,%s,%s) "
                    "ON CONFLICT (run_id,source_id) DO UPDATE SET metadata=EXCLUDED.metadata",
                    (run_id, source.id, Jsonb(obj)),
                )
            for block in analysis.blocks:
                self.connection.execute(
                    "INSERT INTO bilanco.blocks VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (run_id, block.id, block.source_id, Jsonb(block.model_dump(mode="json"))),
                )
            for fact in analysis.facts:
                self.connection.execute(
                    "INSERT INTO bilanco.facts VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (
                        run_id,
                        fact.id,
                        fact.concept,
                        fact.period,
                        fact.value,
                        fact.unit,
                        fact.scale,
                        fact.evidence.block_id,
                        Jsonb(fact.model_dump(mode="json")),
                    ),
                )
            for metric in analysis.metrics:
                self.connection.execute(
                    "INSERT INTO bilanco.metrics VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (
                        run_id,
                        metric.id,
                        metric.period,
                        metric.value,
                        Jsonb(metric.model_dump(mode="json")),
                    ),
                )
            for finding in analysis.findings:
                self.connection.execute(
                    "INSERT INTO bilanco.findings VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                    (run_id, finding.id, Jsonb(finding.model_dump(mode="json"))),
                )
            self.connection.execute(
                "UPDATE bilanco.runs SET status=%s,stage='finished',finished_at=now(),analysis=%s "
                "WHERE id=%s",
                (analysis.status, Jsonb(analysis.model_dump(mode="json")), run_id),
            )

    def recent_runs(self) -> list[tuple]:
        return self.connection.execute(
            "SELECT id, status, stage, started_at FROM bilanco.runs ORDER BY started_at DESC LIMIT 10"
        ).fetchall()
