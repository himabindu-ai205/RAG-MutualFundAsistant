"""Phase 3.3 — Groww-ranked retrieval over Chroma."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from src.ingest.embed import EmbedConfig, get_chunks_by_ids, query_chunks
from src.ingest.registry import load_sources
from src.serve.config import chroma_dir, groww_url_by_scheme

logger = logging.getLogger(__name__)

TOP_K = 5
# Combined score floor after priority boost (smoke hits ~0.55+)
SCORE_THRESHOLD = 0.42

_GROWW_FACTS_ID_BY_SCHEME: dict[str, str] | None = None


def _groww_facts_chunk_id(scheme_tag: str) -> str:
    """Stable Groww Scheme Facts chunk id for a scheme_tag (e.g. groww-flexicap#facts#0)."""
    global _GROWW_FACTS_ID_BY_SCHEME
    if _GROWW_FACTS_ID_BY_SCHEME is None:
        mapping: dict[str, str] = {}
        for row in load_sources():
            if row.publisher.upper() == "GROWW" and row.scheme_tag:
                mapping[row.scheme_tag] = f"{row.source_id}#facts#0"
        _GROWW_FACTS_ID_BY_SCHEME = mapping
    return _GROWW_FACTS_ID_BY_SCHEME.get(scheme_tag, "")


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
    if re.search(r"portfolio\s*turnover|turnover\s*ratio|\bptr\b", q):
        tags.add("portfolio_turnover")
    if re.search(r"dividend|idcw|income\s+distribution", q):
        tags.add("dividend")
    if re.search(r"investment\s+objective|fund\s+objective", q):
        tags.add("investment_objective")
    if re.search(r"asset\s+allocation", q):
        tags.add("asset_allocation")
    return tags


def _is_groww_chunk(chunk: dict[str, Any]) -> bool:
    return str((chunk.get("metadata") or {}).get("publisher") or "").upper() == "GROWW"


def _groww_facts_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Groww Scheme Facts chunks only — ignore noisy full_document windows."""
    return [
        c
        for c in chunks
        if _is_groww_chunk(c)
        and (
            "fact" in str((c.get("metadata") or {}).get("section_title") or "").lower()
            or "#facts#" in str(c.get("chunk_id") or "")
        )
    ]


def _ensure_groww_facts_in_hits(
    hits: list[dict[str, Any]],
    *,
    scheme_tag: str,
    cfg: EmbedConfig,
) -> list[dict[str, Any]]:
    """Pin Groww Scheme Facts into retrieval when semantic search skips the short chunk."""
    if any("#facts#" in str(h.get("chunk_id") or "") for h in hits):
        return hits
    chunk_id = _groww_facts_chunk_id(scheme_tag)
    if not chunk_id:
        return hits
    try:
        facts = get_chunks_by_ids([chunk_id], config=cfg)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Groww facts lookup failed for %s: %s", scheme_tag, exc)
        return hits
    facts = _groww_facts_chunks(facts)
    if not facts:
        return hits
    existing = {h.get("chunk_id") for h in hits}
    prepend = [f for f in facts if f.get("chunk_id") not in existing]
    return prepend + hits if prepend else hits


def _field_hit_rank(chunk: dict[str, Any], fields: set[str]) -> tuple[Any, ...]:
    """Prefer Groww Scheme Facts for fields Groww publishes; else rank SBI PDF chunks."""
    if _is_groww_chunk(chunk):
        facts_rank = 0 if "#facts#" in str(chunk.get("chunk_id") or "") else 1
        return (0, facts_rank, -float(chunk.get("score") or 0.0))
    return (1, *_pdf_citation_rank(chunk, fields))


def _is_full_document_chunk(chunk: dict[str, Any]) -> bool:
    meta = chunk.get("metadata") or {}
    section = str(meta.get("section_title") or "").lower()
    cid = str(chunk.get("chunk_id") or "")
    return section in {"", "full_document"} or "#full#" in cid


def _has_numeric_portfolio_turnover(text: str) -> bool:
    return bool(re.search(r"portfolio turnover ratio[:\s]+[\d.]+", text, re.I))


def _pdf_citation_rank(chunk: dict[str, Any], fields: set[str]) -> tuple[int, int, int, int, float]:
    """Rank SBI PDF chunks: section match, numeric PTR, KIM before SID, then score."""
    meta = chunk.get("metadata") or {}
    doc = str(meta.get("doc_type") or "").upper()
    url = str(meta.get("url") or "").lower()
    text = chunk.get("text") or ""
    is_pdf = url.endswith(".pdf") or doc in {"KIM", "SID"}
    if not is_pdf:
        return (3, 9, 9, 9, 0.0)

    if fields and _chunk_mentions_field(chunk, fields):
        section_rank = 1 if _is_full_document_chunk(chunk) else 0
    else:
        section_rank = 2

    numeric_rank = (
        0
        if "portfolio_turnover" in fields and _has_numeric_portfolio_turnover(text)
        else 1
    )
    kim_rank = 0 if doc == "KIM" or "/kim---" in url else 1
    pri = int(meta.get("priority") or 99)
    score = float(chunk.get("score") or 0.0)
    return (section_rank, numeric_rank, kim_rank, pri, -score)


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
        if f == "ter" and ("expense ratio" in text or "expense" in section):
            return True
        if f == "sip" and ("sip" in text or "minimum" in section):
            return True
        if f == "portfolio_turnover" and (
            "portfolio turnover" in text or "turnover ratio" in text
        ):
            return True
        if f == "dividend" and ("dividend" in text or "idcw" in text):
            return True
        if f == "investment_objective" and (
            "investment objective" in text or "objective of the scheme" in text
        ):
            return True
        if f == "asset_allocation" and (
            "asset allocation" in text or "asset allocation" in section
        ):
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

    if scheme_tag and hits:
        hits = _ensure_groww_facts_in_hits(hits, scheme_tag=scheme_tag, cfg=cfg)

    fields = _field_keywords(question)
    # Ensure at least one Groww chunk when scheme is named
    groww_hits = [
        h
        for h in hits
        if _is_groww_chunk(h) or int((h.get("metadata") or {}).get("priority") or 99) == 1
    ]
    if scheme_tag and groww_hits:
        if fields:
            groww_field = [
                h for h in _groww_facts_chunks(groww_hits) if _chunk_mentions_field(h, fields)
            ]
            sbi_field = [
                h
                for h in hits
                if h not in groww_hits and _chunk_mentions_field(h, fields)
            ]
            if sbi_field and not groww_field:
                # Groww lacks this field — lead with best matching KIM/SID PDF chunks
                sbi_field = sorted(sbi_field, key=lambda c: _pdf_citation_rank(c, fields))
                rest = [h for h in hits if h not in sbi_field and h not in groww_hits]
                hits = sbi_field + groww_hits + rest
            else:
                others = [h for h in hits if h not in groww_hits]
                hits = groww_hits + others
        else:
            others = [h for h in hits if h not in groww_hits]
            hits = groww_hits + others

    # Prefer chunks that mention the asked field; Groww facts before SBI PDF sections
    if fields:
        field_hits = [h for h in hits if _chunk_mentions_field(h, fields)]
        if field_hits:
            field_hits = sorted(field_hits, key=lambda c: _field_hit_rank(c, fields))
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


def best_pdf_citation(chunks: list[dict[str, Any]], question: str) -> tuple[str, str]:
    """Best SBI PDF URL when Groww lacks the asked field."""
    fields = _field_keywords(question)
    candidates: list[dict[str, Any]] = []
    for c in chunks:
        meta = c.get("metadata") or {}
        if str(meta.get("publisher") or "").upper() == "GROWW":
            continue
        url = str(meta.get("url") or "")
        if url.startswith("http"):
            candidates.append(c)

    if fields:
        matched = [c for c in candidates if _chunk_mentions_field(c, fields)]
        if matched:
            candidates = matched
        # Portfolio turnover: prefer KIM numeric ratio (page 9) over SID policy text
        if "portfolio_turnover" in fields:
            numeric_kim = [
                c
                for c in candidates
                if str((c.get("metadata") or {}).get("doc_type") or "").upper() == "KIM"
                and _has_numeric_portfolio_turnover(c.get("text") or "")
            ]
            if numeric_kim:
                candidates = numeric_kim

    if not candidates:
        return "", ""

    best = min(candidates, key=lambda c: _pdf_citation_rank(c, fields))
    meta = best.get("metadata") or {}
    return str(meta.get("url") or ""), str(meta.get("retrieved_on") or "")


def groww_has_field(chunks: list[dict[str, Any]], question: str) -> bool:
    """True when Groww Scheme Facts contains the specific field asked about."""
    fields = _field_keywords(question)
    groww_all = [c for c in chunks if _is_groww_chunk(c)]
    groww = _groww_facts_chunks(chunks) or groww_all
    if not groww:
        return False
    if not fields:
        return True
    if any(_chunk_mentions_field(c, fields) for c in groww):
        return True
    blob = "\n".join(c.get("text") or "" for c in groww)
    if "ter" in fields and re.search(r"Expense Ratio:\s*[\d.]+%", blob, re.I):
        return True
    if "exit_load" in fields and re.search(r"Exit Load:", blob, re.I):
        return True
    if "sip" in fields and re.search(r"Min Sip:", blob, re.I):
        return True
    if "nav" in fields and re.search(r"\bNav:\s*₹", blob, re.I):
        return True
    return False


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
