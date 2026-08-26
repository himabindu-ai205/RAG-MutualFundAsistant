"""Load docs/sources.csv registry rows for ingest."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES_CSV = ROOT / "docs" / "sources.csv"

ALLOWED_HOST_SUFFIXES = (
    "groww.in",
    "sbimf.com",
    "amfiindia.com",
    "sebi.gov.in",
)

GROWW_ALLOWED_PATHS = {
    "/mutual-funds/sbi-large-cap-direct-plan-growth",
    "/mutual-funds/sbi-flexicap-fund-direct-growth",
    "/mutual-funds/sbi-elss-tax-saver-fund-direct-growth",
    "/mutual-funds/sbi-contra-fund-direct-growth",
    "/mutual-funds/sbi-small-midcap-fund-direct-growth",
}


@dataclass(frozen=True)
class SourceRow:
    source_id: str
    url: str
    publisher: str
    doc_type: str
    scheme: str
    scheme_tag: str
    local_path: str
    retrieved_on: str
    priority: int

    def local_file(self, root: Path | None = None) -> Path:
        base = root or ROOT
        return base / self.local_path


def host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return any(host == s or host.endswith("." + s) for s in ALLOWED_HOST_SUFFIXES)


def groww_path_allowed(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host != "groww.in":
        return True
    path = parsed.path.rstrip("/") or "/"
    return path in GROWW_ALLOWED_PATHS


def load_sources(csv_path: Path | None = None) -> list[SourceRow]:
    path = csv_path or DEFAULT_SOURCES_CSV
    rows: list[SourceRow] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            rows.append(
                SourceRow(
                    source_id=raw["source_id"].strip(),
                    url=raw["url"].strip(),
                    publisher=raw["publisher"].strip(),
                    doc_type=raw["doc_type"].strip(),
                    scheme=raw["scheme"].strip(),
                    scheme_tag=raw["scheme_tag"].strip(),
                    local_path=raw["local_path"].strip().replace("\\", "/"),
                    retrieved_on=(raw.get("retrieved_on") or "").strip(),
                    priority=int(raw["priority"]),
                )
            )
    return rows


def write_sources(rows: list[SourceRow], csv_path: Path | None = None) -> None:
    path = csv_path or DEFAULT_SOURCES_CSV
    fieldnames = [
        "source_id",
        "url",
        "publisher",
        "doc_type",
        "scheme",
        "scheme_tag",
        "local_path",
        "retrieved_on",
        "priority",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "source_id": row.source_id,
                    "url": row.url,
                    "publisher": row.publisher,
                    "doc_type": row.doc_type,
                    "scheme": row.scheme,
                    "scheme_tag": row.scheme_tag,
                    "local_path": row.local_path,
                    "retrieved_on": row.retrieved_on,
                    "priority": row.priority,
                }
            )
