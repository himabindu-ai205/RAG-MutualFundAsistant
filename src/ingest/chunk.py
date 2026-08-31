"""Phase 2.3 — Chunk parsed documents with metadata.

Order: Groww first, then supporting docs. Prefer section-aware splits;
fallback to ~500–800 token windows with 10–15% overlap.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from src.ingest.parse import ParsedDocument, parse_all
from src.ingest.registry import ROOT, load_sources

logger = logging.getLogger(__name__)

# ~token proxy via whitespace words (good enough for ingest sizing).
MIN_TOKENS = 500
TARGET_TOKENS = 650
MAX_TOKENS = 800
OVERLAP_RATIO = 0.12  # 10–15%
MICRO_SECTION_TOKENS = 50  # merge Groww micro-sections into Facts
# Cap SID/KIM full windows so branch lists / legalese do not dominate the index
MAX_FULL_WINDOWS_SID = 10
MAX_FULL_WINDOWS_KIM = 10
MAX_FULL_WINDOWS_DEFAULT = 20

SECTION_TITLE_MAP = {
    "full": "full_document",
    "exit_load": "Exit Load",
    "expense_ratio": "Expense Ratio",
    "minimum_investment": "Minimum Investment",
    "lock_in": "Lock-in",
    "risk_benchmark": "Riskometer / Benchmark",
    "riskometer": "Riskometer",
    "benchmark": "Benchmark",
    "investment_objective": "Investment Objective",
    "asset_allocation": "Asset Allocation",
    "portfolio_turnover": "Portfolio Turnover",
    "risk_factors": "Risk Factors",
    "facts": "Scheme Facts",
    "hub": "Hub Overview",
}

# Groww micro fact sections already covered by the Scheme Facts chunk
GROWW_MERGE_SECTION_KEYS = {
    "exit_load",
    "expense_ratio",
    "minimum_investment",
    "lock_in",
    "risk_benchmark",
    "riskometer",
    "benchmark",
}


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    source_id: str
    url: str
    scheme: str
    scheme_tag: str
    doc_type: str
    publisher: str
    section_title: str
    retrieved_on: str
    priority: int
    local_path: str  # ingest-only; never cite in UI

    def metadata(self) -> dict[str, str | int]:
        """Chroma-friendly flat metadata (no nested objects)."""
        return {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
            "url": self.url,
            "scheme": self.scheme,
            "scheme_tag": self.scheme_tag,
            "doc_type": self.doc_type,
            "publisher": self.publisher,
            "section_title": self.section_title,
            "retrieved_on": self.retrieved_on,
            "priority": int(self.priority),
            "local_path": self.local_path,
        }


def estimate_tokens(text: str) -> int:
    words = re.findall(r"\S+", text)
    return max(1, len(words)) if text.strip() else 0


def _window_texts(text: str, *, max_windows: int | None = None) -> list[str]:
    """Sliding windows of TARGET_TOKENS with OVERLAP_RATIO overlap."""
    words = re.findall(r"\S+", text)
    if not words:
        return []
    if len(words) <= MAX_TOKENS:
        return [" ".join(words)]

    step = max(1, int(TARGET_TOKENS * (1 - OVERLAP_RATIO)))
    windows: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + TARGET_TOKENS)
        # Prefer ending near a sentence-ish boundary when possible
        if end < len(words):
            for j in range(end, max(start + MIN_TOKENS, end - 40), -1):
                if words[j - 1].endswith((".", "?", "!", ";", ":")):
                    end = j
                    break
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            windows.append(chunk)
        if end >= len(words):
            break
        start += step
        if max_windows is not None and len(windows) >= max_windows:
            break
    return windows


def _full_window_limit(doc: ParsedDocument) -> int:
    dt = (doc.doc_type or "").upper()
    if dt == "SID":
        return MAX_FULL_WINDOWS_SID
    if dt == "KIM":
        return MAX_FULL_WINDOWS_KIM
    if dt == "HUB" or doc.facts.get("corpus_role") == "hub":
        return 1
    return MAX_FULL_WINDOWS_DEFAULT


def _is_groww(doc: ParsedDocument) -> bool:
    return doc.publisher.upper() == "GROWW" or doc.doc_type == "groww_scheme"


def _make_chunk(
    doc: ParsedDocument,
    *,
    section_key: str,
    index: int,
    text: str,
) -> Chunk | None:
    body = text.strip()
    if estimate_tokens(body) < 20 and section_key not in {"facts", "hub", "lock_in", "exit_load"}:
        if estimate_tokens(body) < 5:
            return None
    title = SECTION_TITLE_MAP.get(section_key, section_key.replace("_", " ").title())
    chunk_id = f"{doc.source_id}#{section_key}#{index}"
    return Chunk(
        chunk_id=chunk_id,
        text=body,
        source_id=doc.source_id,
        url=doc.url,
        scheme=doc.scheme,
        scheme_tag=doc.scheme_tag,
        doc_type=doc.doc_type,
        publisher=doc.publisher,
        section_title=title,
        retrieved_on=doc.retrieved_on,
        priority=int(doc.priority),
        local_path=doc.local_path,
    )


def _dedupe(chunks: list[Chunk]) -> list[Chunk]:
    seen: set[str] = set()
    unique: list[Chunk] = []
    for ch in chunks:
        key = ch.text.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(ch)
    return unique


def chunk_document(doc: ParsedDocument) -> list[Chunk]:
    """Chunk one parsed document (section-aware + overlapping windows)."""
    chunks: list[Chunk] = []
    groww = _is_groww(doc)
    is_hub = doc.doc_type == "hub" or doc.facts.get("corpus_role") == "hub"

    # 1) Dedicated facts chunk for Groww (high-signal primary fields)
    if doc.facts and groww:
        order = [
            "category",
            "expense_ratio",
            "min_sip",
            "min_lumpsum",
            "nav",
            "exit_load",
            "lock_in",
            "riskometer",
            "benchmark",
            "aum",
        ]
        keys = [k for k in order if k in doc.facts] + [
            k for k in doc.facts if k not in order and k != "corpus_role"
        ]
        fact_lines = [f"{k.replace('_', ' ').title()}: {doc.facts[k]}" for k in keys]
        fact_text = f"{doc.scheme} — scheme facts from Groww\n" + "\n".join(fact_lines)
        c = _make_chunk(doc, section_key="facts", index=0, text=fact_text)
        if c:
            chunks.append(c)

    # 1b) Hub overview only (no noisy full-page windows)
    if is_hub and "hub" in doc.sections:
        c = _make_chunk(doc, section_key="hub", index=0, text=doc.sections["hub"])
        if c:
            chunks.append(c)
        return _dedupe(chunks)

    # 2) Named sections (skip full here; windowed below)
    section_index: dict[str, int] = {}
    for key, section_text in doc.sections.items():
        if key in {"full", "hub"} or not section_text.strip():
            continue
        # Groww: fold micro fact sections into Scheme Facts (already emitted)
        if groww and key in GROWW_MERGE_SECTION_KEYS:
            if estimate_tokens(section_text) <= MICRO_SECTION_TOKENS:
                continue
        if estimate_tokens(section_text) <= MAX_TOKENS:
            idx = section_index.get(key, 0)
            c = _make_chunk(doc, section_key=key, index=idx, text=section_text)
            section_index[key] = idx + 1
            if c:
                chunks.append(c)
        else:
            for part in _window_texts(section_text):
                idx = section_index.get(key, 0)
                c = _make_chunk(doc, section_key=key, index=idx, text=part)
                section_index[key] = idx + 1
                if c:
                    chunks.append(c)

    # 3) Overlapping windows over full text (coverage), capped for SID/KIM
    full = doc.sections.get("full") or doc.text
    max_full = _full_window_limit(doc)
    for i, part in enumerate(_window_texts(full, max_windows=max_full)):
        c = _make_chunk(doc, section_key="full", index=i, text=part)
        if c:
            chunks.append(c)

    return _dedupe(chunks)


def chunk_all(
    docs: list[ParsedDocument] | None = None,
    *,
    skip_missing: bool = True,
) -> list[Chunk]:
    """Parse (if needed) and chunk in Groww-first priority order."""
    if docs is None:
        docs = parse_all(load_sources(), skip_missing=skip_missing)

    docs_sorted = sorted(
        docs,
        key=lambda d: (d.priority, 0 if d.publisher.upper() == "GROWW" else 1, d.source_id),
    )

    all_chunks: list[Chunk] = []
    for doc in docs_sorted:
        doc_chunks = chunk_document(doc)
        all_chunks.extend(doc_chunks)
        logger.info(
            "Chunked %s (%s) -> %d chunks",
            doc.source_id,
            doc.publisher,
            len(doc_chunks),
        )
    return all_chunks


def summarize(chunks: list[Chunk]) -> str:
    by_pub: dict[str, int] = {}
    by_pri: dict[int, int] = {}
    by_section: dict[str, int] = {}
    groww = 0
    for c in chunks:
        by_pub[c.publisher] = by_pub.get(c.publisher, 0) + 1
        by_pri[c.priority] = by_pri.get(c.priority, 0) + 1
        by_section[c.section_title] = by_section.get(c.section_title, 0) + 1
        if c.publisher.upper() == "GROWW":
            groww += 1
    full_share = by_section.get("full_document", 0) / max(1, len(chunks))
    return (
        f"Total chunks: {len(chunks)} | Groww: {groww} | "
        f"by publisher: {by_pub} | by priority: {by_pri} | "
        f"full_document_share={full_share:.1%}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 2.3 corpus chunker")
    parser.add_argument("--skip-missing", action="store_true", default=True)
    parser.add_argument("--require-all", action="store_true", help="Fail on missing files")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional JSONL output path (default: data/chunks.jsonl)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--source-id",
        action="append",
        default=[],
        help="Only chunk these source_id values",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    rows = load_sources()
    if args.source_id:
        wanted = set(args.source_id)
        rows = [r for r in rows if r.source_id in wanted]

    docs = parse_all(rows, skip_missing=not args.require_all)
    chunks = chunk_all(docs)

    out_path = args.out or (ROOT / "data" / "chunks.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(asdict(ch), ensure_ascii=False) + "\n")

    print(summarize(chunks))
    print(f"Wrote {out_path}")
    if chunks and chunks[0].publisher.upper() != "GROWW" and any(
        c.publisher.upper() == "GROWW" for c in chunks
    ):
        first_groww = next(i for i, c in enumerate(chunks) if c.publisher.upper() == "GROWW")
        if first_groww != 0:
            logger.warning("Expected Groww chunks first; first Groww at index %d", first_groww)
    return 0


if __name__ == "__main__":
    sys.exit(main())
