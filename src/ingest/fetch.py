"""Phase 2.1 — Document fetcher.

Order: Groww HTML (required) → register local KIM/SID PDFs → shared official HTML.
Rejects hosts outside the allowlist. Fails the build if any Groww fetch fails.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import replace
from datetime import date
from pathlib import Path

import httpx

from src.ingest.registry import (
    ROOT,
    SourceRow,
    groww_path_allowed,
    host_allowed,
    load_sources,
    write_sources,
)

logger = logging.getLogger(__name__)

USER_AGENT = "RAG-MutualFundAssistant/0.1 (facts-only corpus fetch; public pages only)"
REQUEST_DELAY_SEC = 0.75
# CI / flaky network: retry primary + shared fetches with backoff
FETCH_MAX_ATTEMPTS = 3
FETCH_RETRY_BACKOFF_SEC = 2.0


class FetchError(RuntimeError):
    """Raised when a required fetch fails."""


def _is_pdf_row(row: SourceRow) -> bool:
    return row.doc_type in {"KIM", "SID"} or row.local_path.lower().endswith(".pdf")


def _is_html_row(row: SourceRow) -> bool:
    return not _is_pdf_row(row)


def _validate_url(row: SourceRow) -> None:
    if not host_allowed(row.url):
        raise FetchError(f"Host not allowlisted for {row.source_id}: {row.url}")
    if not groww_path_allowed(row.url):
        raise FetchError(f"Groww path not allowlisted for {row.source_id}: {row.url}")


def _http_get(
    client: httpx.Client,
    url: str,
    *,
    max_attempts: int = FETCH_MAX_ATTEMPTS,
) -> httpx.Response:
    """GET with polite retries (transient network / 429 / 5xx)."""
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.get(url)
            if response.status_code == 429 or response.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
            return response
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt >= max_attempts:
                break
            delay = FETCH_RETRY_BACKOFF_SEC * attempt
            logger.warning(
                "Fetch retry %d/%d for %s after %s (sleep %.1fs)",
                attempt,
                max_attempts,
                url,
                exc,
                delay,
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def fetch_groww_html(
    rows: list[SourceRow],
    *,
    client: httpx.Client,
    root: Path = ROOT,
    today: str | None = None,
) -> list[SourceRow]:
    """Fetch all GROWW / groww_scheme rows. Fail if any request fails."""
    stamp = today or date.today().isoformat()
    groww_rows = [
        r
        for r in rows
        if r.publisher.upper() == "GROWW" or r.doc_type == "groww_scheme"
    ]
    if len(groww_rows) < 5:
        raise FetchError(
            f"Expected at least 5 Groww sources in registry, found {len(groww_rows)}"
        )

    updated: dict[str, SourceRow] = {}
    for row in groww_rows:
        _validate_url(row)
        dest = row.local_file(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Groww fetch %s -> %s", row.source_id, dest)
        try:
            response = _http_get(client, row.url)
        except Exception as exc:  # noqa: BLE001 — fail closed for primary source
            raise FetchError(
                f"Groww fetch failed for {row.source_id} ({row.url}): {exc}"
            ) from exc
        dest.write_text(response.text, encoding="utf-8")
        updated[row.source_id] = replace(row, retrieved_on=stamp)
        time.sleep(REQUEST_DELAY_SEC)

    return [updated.get(r.source_id, r) for r in rows]


def register_pdfs(rows: list[SourceRow], *, root: Path = ROOT) -> list[SourceRow]:
    """Confirm local KIM/SID PDFs exist; do not re-download."""
    updated: list[SourceRow] = []
    for row in rows:
        if not _is_pdf_row(row):
            updated.append(row)
            continue
        _validate_url(row)
        path = row.local_file(root)
        if not path.is_file():
            raise FetchError(f"Missing local PDF for {row.source_id}: {path}")
        stamp = row.retrieved_on or date.today().isoformat()
        logger.info("PDF registered %s (%s bytes)", row.source_id, path.stat().st_size)
        updated.append(replace(row, retrieved_on=stamp))
    return updated


def fetch_shared_html(
    rows: list[SourceRow],
    *,
    client: httpx.Client,
    root: Path = ROOT,
    today: str | None = None,
    fail_soft: bool = True,
) -> list[SourceRow]:
    """Fetch non-Groww HTML registry rows into docs/corpus/shared (and similar)."""
    stamp = today or date.today().isoformat()
    updated: list[SourceRow] = []
    for row in rows:
        if row.publisher.upper() == "GROWW" or row.doc_type == "groww_scheme":
            updated.append(row)
            continue
        if _is_pdf_row(row):
            updated.append(row)
            continue
        if not _is_html_row(row):
            updated.append(row)
            continue

        _validate_url(row)
        dest = row.local_file(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Shared HTML fetch %s -> %s", row.source_id, dest)
        try:
            response = _http_get(client, row.url)
            dest.write_bytes(response.content)
            updated.append(replace(row, retrieved_on=stamp))
        except Exception as exc:  # noqa: BLE001
            if fail_soft:
                logger.warning(
                    "Shared fetch skipped for %s (%s): %s",
                    row.source_id,
                    row.url,
                    exc,
                )
                updated.append(row)
            else:
                raise FetchError(
                    f"Shared fetch failed for {row.source_id} ({row.url}): {exc}"
                ) from exc
        time.sleep(REQUEST_DELAY_SEC)
    return updated


def run_fetch(
    *,
    sources_csv: Path | None = None,
    root: Path = ROOT,
    skip_shared: bool = False,
    fail_soft_shared: bool = True,
) -> list[SourceRow]:
    rows = load_sources(sources_csv)
    for row in rows:
        _validate_url(row)

    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,*/*"}
    with httpx.Client(follow_redirects=True, timeout=45.0, headers=headers) as client:
        # 1) Groww first (required)
        rows = fetch_groww_html(rows, client=client, root=root)
        # 2) Local PDFs
        rows = register_pdfs(rows, root=root)
        # 3) Shared official HTML
        if not skip_shared:
            rows = fetch_shared_html(
                rows, client=client, root=root, fail_soft=fail_soft_shared
            )

    write_sources(rows, sources_csv)
    return rows


def _summary(rows: list[SourceRow], root: Path = ROOT) -> str:
    groww_ok = sum(
        1
        for r in rows
        if (r.publisher.upper() == "GROWW" or r.doc_type == "groww_scheme")
        and r.local_file(root).is_file()
    )
    pdf_ok = sum(1 for r in rows if _is_pdf_row(r) and r.local_file(root).is_file())
    shared_ok = sum(
        1
        for r in rows
        if _is_html_row(r)
        and r.publisher.upper() != "GROWW"
        and r.doc_type != "groww_scheme"
        and r.local_file(root).is_file()
    )
    return (
        f"Groww HTML on disk: {groww_ok}/5+ | "
        f"PDFs registered: {pdf_ok} | "
        f"Shared HTML on disk: {shared_ok}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 2.1 corpus fetcher (Groww first)")
    parser.add_argument(
        "--sources",
        type=Path,
        default=None,
        help="Path to sources.csv (default: docs/sources.csv)",
    )
    parser.add_argument(
        "--skip-shared",
        action="store_true",
        help="Only fetch Groww + register PDFs",
    )
    parser.add_argument(
        "--strict-shared",
        action="store_true",
        help="Fail if any shared HTML fetch fails (default: soft-skip)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        rows = run_fetch(
            sources_csv=args.sources,
            skip_shared=args.skip_shared,
            fail_soft_shared=not args.strict_shared,
        )
    except FetchError as exc:
        logger.error("%s", exc)
        logger.error("Index incomplete: Groww primary fetch must succeed.")
        return 1

    print(_summary(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
