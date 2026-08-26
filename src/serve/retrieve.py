"""Phase 3.3 — Groww-ranked retrieval over Chroma."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from src.ingest.embed import EmbedConfig, query_chunks
from src.serve.config import chroma_dir, groww_url_by_scheme

logger = logging.getLogger(__name__)

TOP_K = 5
# Combined score floor after priority boost (smoke hits ~0.55+)
SCORE_THRESHOLD = 0.42


@dataclass
class RetrievalResult:
    chunks: list[dict[str, Any]]
    scheme_tag: str | None
    low_score: bool
    groww_url: str | None


def _embed_config() -> EmbedConfig:
    return EmbedConfig(chroma_dir=chroma_dir())


def _field_keywords(question: str) -> set[str]:
    q = question.lower()
    tags: set[str] = set()
    if re.search(r"\bnav\b|net\s+asset\s+value", q):
        tags.add("nav")
    if re.search(r"exit\s*load", q):
        tags.add("exit_load")
    if re.search(r"\bter\b|expense\s*ratio", q):
        tags.add("ter")
    if re.search(r"\bsip\b|min(?:imum)?\s+investment|lumpsum", q):
        tags.add("sip")
    if re.search(r"lock[\s-]*in", q):
        tags.add("lock_in")
    if re.search(r"riskometer|risk[\s-]*o?meter", q):
        tags.add("riskometer")
    if re.search(r"benchmark", q):
        tags.add("benchmark")
    return tags


def _chunk_mentions_field(chunk: dict[str, Any], fields: set[str]) -> bool:
    if not fields:
        return True
    meta = chunk.get("metadata") or {}
    kw = set(str(meta.get("keywords") or "").split(",")) - {""}
    text = (chunk.get("text") or "").lower()
    section = str(meta.get("section_title") or "").lower()
    for f in fields:
        if f in kw:
            return True
        if f.replace("_", " ") in text or f.replace("_", "-") in text:
            return True
        if f == "nav" and ("nav" in text or "net asset" in text):
            return True
        if f == "exit_load" and "exit load" in section:
            return True
        if f == "lock_in" and "lock" in section:
            return True
        if f == "ter" and ("expense" in section or "ter" in text):
            return True
        if f == "sip" and ("sip" in text or "minimum" in section):
            return True
    return False


def retrieve(
    question: str,
    *,
    scheme_tag: str | None = None,
    intent: str = "factual",
    top_k: int = TOP_K,
) -> RetrievalResult:
    """Search Groww + SBI; re-rank by priority then score; prefer Groww for named schemes."""
    cfg = _embed_config()
    where: dict[str, Any] | None = None
    if scheme_tag:
        where = {"scheme_tag": scheme_tag}

    try:
        hits = query_chunks(question, n_results=max(top_k * 2, 8), config=cfg, where=where)
    except Exception as exc:  # noqa: BLE001
        logger.error("Chroma query failed: %s", exc)
        hits = []

    # If scheme filter returned nothing, retry without filter
    if scheme_tag and not hits:
        try:
            hits = query_chunks(question, n_results=max(top_k * 2, 8), config=cfg, where=None)
        except Exception as exc:  # noqa: BLE001
            logger.error("Chroma fallback query failed: %s", exc)
            hits = []

    # process_howto: soft-prefer statement / hub / education chunks
    if intent == "process_howto" and hits:
        preferred = [
            h
            for h in hits
            if str((h.get("metadata") or {}).get("doc_type") or "").lower()
            in {"hub", "statement_guide", "faq", "education", "ter"}
            or str((h.get("metadata") or {}).get("scheme_tag") or "") == "shared"
        ]
        if preferred:
            rest = [h for h in hits if h not in preferred]
            hits = preferred + rest

    fields = _field_keywords(question)
    # Ensure at least one Groww chunk when scheme is named
    groww_hits = [
        h
        for h in hits
        if str((h.get("metadata") or {}).get("publisher") or "").upper() == "GROWW"
        or int((h.get("metadata") or {}).get("priority") or 99) == 1
    ]
    if scheme_tag and groww_hits:
        # Put Groww first, then fill with other high-score hits
        others = [h for h in hits if h not in groww_hits]
        hits = groww_hits + others

    # Prefer chunks that mention the asked field among Groww first
    if fields:
        field_hits = [h for h in hits if _chunk_mentions_field(h, fields)]
        if field_hits:
            rest = [h for h in hits if h not in field_hits]
            hits = field_hits + rest

    selected = hits[:top_k]
    best = float(selected[0]["score"]) if selected else 0.0
    low = (not selected) or best < SCORE_THRESHOLD

    groww_urls = groww_url_by_scheme()
    return RetrievalResult(
        chunks=selected,
        scheme_tag=scheme_tag,
        low_score=low,
        groww_url=groww_urls.get(scheme_tag or "") if scheme_tag else None,
    )


def choose_citation_url(chunks: list[dict[str, Any]], *, scheme_tag: str | None) -> tuple[str, str]:
    """Prefer Groww URL when Groww chunks are present; else first allowlisted chunk URL.

    Returns (url, retrieved_on).
    """
    groww_urls = groww_url_by_scheme()
    groww_chunks = [
        c
        for c in chunks
        if str((c.get("metadata") or {}).get("publisher") or "").upper() == "GROWW"
    ]
    if groww_chunks:
        meta = groww_chunks[0].get("metadata") or {}
        url = str(meta.get("url") or "")
        if scheme_tag and scheme_tag in groww_urls:
            url = groww_urls[scheme_tag]
        return url, str(meta.get("retrieved_on") or "")

    for c in chunks:
        meta = c.get("metadata") or {}
        url = str(meta.get("url") or "")
        if url.startswith("http"):
            return url, str(meta.get("retrieved_on") or "")

    if scheme_tag and scheme_tag in groww_urls:
        return groww_urls[scheme_tag], ""
    return "", ""
