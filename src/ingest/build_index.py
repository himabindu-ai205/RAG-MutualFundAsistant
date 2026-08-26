"""Phase 2.5 — Single offline index build.

Default path: Groww HTML (required) → register KIM/SID PDFs → shared HTML
→ parse → chunk → embed into data/chroma/.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.ingest.chunk import chunk_all, summarize as summarize_chunks
from src.ingest.embed import (
    DEFAULT_CHROMA_DIR,
    DEFAULT_CHUNKS_JSONL,
    DEFAULT_MODEL,
    EmbedConfig,
    embed_chunks,
    query_chunks,
)
from src.ingest.fetch import FetchError, run_fetch
from src.ingest.parse import parse_all
from src.ingest.registry import ROOT, load_sources

logger = logging.getLogger(__name__)

SMOKE_QUERIES = ("ELSS lock-in", "exit load Flexicap")


def _require_groww_on_disk() -> None:
    rows = load_sources()
    groww = [
        r
        for r in rows
        if r.publisher.upper() == "GROWW" or r.doc_type == "groww_scheme"
    ]
    missing = [r.source_id for r in groww if not r.local_file(ROOT).is_file()]
    if len(groww) < 5:
        raise FetchError(
            f"Expected at least 5 Groww sources in registry, found {len(groww)}"
        )
    if missing:
        raise FetchError(
            "Groww snapshots missing on disk (index incomplete): "
            + ", ".join(missing)
            + ". Run without --skip-fetch."
        )


def _write_chunks_jsonl(chunks: list[Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(asdict(ch), ensure_ascii=False) + "\n")
    logger.info("Wrote %s (%d chunks)", path, len(chunks))


def _print_smoke(cfg: EmbedConfig) -> None:
    for q in SMOKE_QUERIES:
        hits = query_chunks(q, n_results=5, config=cfg)
        print(f"\nSMOKE: {q!r}")
        for h in hits:
            meta = h["metadata"]
            print(
                f"  pri={meta.get('priority')} pub={meta.get('publisher')} "
                f"scheme={meta.get('scheme_tag')} section={meta.get('section_title')} "
                f"score={h['score']:.3f} id={h['chunk_id']}"
            )
        if hits and int(hits[0]["metadata"].get("priority") or 99) != 1:
            logger.warning("Top hit is not priority=1 (Groww) for %r", q)


def build_index(
    *,
    skip_fetch: bool = False,
    skip_shared: bool = False,
    fail_soft_shared: bool = True,
    skip_missing_parse: bool = True,
    chunks_path: Path = DEFAULT_CHUNKS_JSONL,
    embed_config: EmbedConfig | None = None,
    reset: bool = True,
    smoke: bool = False,
) -> dict[str, Any]:
    """Run fetch → parse → chunk → embed. Returns embed summary plus stage counts."""
    cfg = embed_config or EmbedConfig()

    if skip_fetch:
        logger.info("Skipping fetch; using local corpus files")
        _require_groww_on_disk()
    else:
        logger.info("Stage 1/4 fetch: Groww HTML → PDFs → shared HTML")
        run_fetch(skip_shared=skip_shared, fail_soft_shared=fail_soft_shared)
        _require_groww_on_disk()

    logger.info("Stage 2/4 parse")
    docs = parse_all(load_sources(), skip_missing=skip_missing_parse)
    groww_docs = sum(1 for d in docs if d.publisher.upper() == "GROWW")
    if groww_docs < 5:
        raise FetchError(
            f"Parsed only {groww_docs} Groww documents; need 5 before the index is complete"
        )

    logger.info("Stage 3/4 chunk")
    chunks = chunk_all(docs)
    groww_chunks = sum(1 for c in chunks if c.publisher.upper() == "GROWW")
    if groww_chunks == 0:
        raise FetchError("No Groww chunks produced; refusing to write a PDFs-only index")
    _write_chunks_jsonl(chunks, chunks_path)
    print(summarize_chunks(chunks))

    logger.info("Stage 4/4 embed")
    summary = embed_chunks(chunks, config=cfg, reset=reset)
    summary = {
        **summary,
        "parsed_docs": len(docs),
        "groww_docs": groww_docs,
        "chunks_path": str(chunks_path),
    }

    print(
        f"Embedded {summary['count']} chunks "
        f"(Groww={summary['groww_chunks']}) -> {summary['chroma_dir']} "
        f"[{summary['collection']}] model={summary['model']}"
    )
    print(f"by publisher: {summary['by_publisher']}")

    if smoke:
        _print_smoke(cfg)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 2.5: build Chroma index (Groww fetch → PDFs → shared → parse → chunk → embed)"
        )
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Reuse docs/corpus snapshots; still requires all five Groww HTML files",
    )
    parser.add_argument(
        "--skip-shared",
        action="store_true",
        help="Fetch Groww + register PDFs only (no shared HTML)",
    )
    parser.add_argument(
        "--strict-shared",
        action="store_true",
        help="Fail if any shared HTML fetch fails (default: soft-skip)",
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="Fail parse if a registry local file is missing (default: skip missing)",
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_JSONL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--chroma-dir", type=Path, default=DEFAULT_CHROMA_DIR)
    parser.add_argument("--no-reset", action="store_true")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="After embed, run ELSS lock-in / Flexicap exit-load smoke queries",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    cfg = EmbedConfig(model_name=args.model, chroma_dir=args.chroma_dir)
    try:
        build_index(
            skip_fetch=args.skip_fetch,
            skip_shared=args.skip_shared,
            fail_soft_shared=not args.strict_shared,
            skip_missing_parse=not args.require_all,
            chunks_path=args.chunks,
            embed_config=cfg,
            reset=not args.no_reset,
            smoke=args.smoke,
        )
    except FetchError as exc:
        logger.error("%s", exc)
        logger.error("Index incomplete: Groww primary ingest must succeed.")
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
