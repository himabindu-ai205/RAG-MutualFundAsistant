"""Online pipeline: classify → refuse | retrieve → generate → validate."""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any
from urllib.parse import urlparse

from src.serve.classify import Classification, classify
from src.serve.generate import generate_answer
from src.serve.refuse import not_in_corpus, refuse
from src.serve.retrieve import retrieve
from src.serve.validate import validate_response

logger = logging.getLogger(__name__)

REFUSAL_INTENTS = {"advisory", "comparative", "performance", "pii", "out_of_scope"}


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _groww_has_field(chunks: list[dict[str, Any]], question: str) -> bool:
    """True if a Groww chunk likely contains the asked field."""
    q = question.lower()
    needles: list[str] = []
    if re.search(r"\bnav\b|net\s+asset\s+value", q):
        needles += ["nav", "latest nav", "net asset"]
    if re.search(r"exit\s*load", q):
        needles += ["exit load", "exit_load"]
    if re.search(r"\bter\b|expense\s*ratio", q):
        needles += ["expense ratio", "expense_ratio", "ter"]
    if re.search(r"\bsip\b|min(?:imum)?\s+(sip|investment|lumpsum)", q):
        needles += ["min sip", "sip", "lumpsum", "minimum"]
    if re.search(r"lock[\s-]*in", q):
        needles += ["lock-in", "lock in", "lock_in", "3y"]
    if re.search(r"riskometer|risk[\s-]*o?meter", q):
        needles += ["riskometer", "very high risk", "high risk"]
    if re.search(r"benchmark", q):
        needles += ["benchmark"]
    if not needles:
        # No specific field — any Groww chunk counts as having scheme context
        return any(
            str((c.get("metadata") or {}).get("publisher") or "").upper() == "GROWW"
            for c in chunks
        )

    for c in chunks:
        meta = c.get("metadata") or {}
        if str(meta.get("publisher") or "").upper() != "GROWW":
            continue
        blob = f"{meta.get('section_title', '')}\n{c.get('text', '')}\n{meta.get('keywords', '')}".lower()
        if any(n in blob for n in needles):
            return True
    return False


def answer_question(question: str) -> dict[str, Any]:
    """Full serve path. Never logs raw PII queries."""
    request_id = str(uuid.uuid4())
    t0 = time.perf_counter()
    text = (question or "").strip()
    if not text:
        return {"error": "question_required", "request_id": request_id}

    clf: Classification = classify(text)
    intent = clf.intent
    scheme = clf.scheme_tag

    log_q = "[redacted]" if clf.has_pii or intent == "pii" else text[:120]
    logger.info(
        "request_id=%s intent=%s scheme=%s q=%r",
        request_id,
        intent,
        scheme,
        log_q,
    )

    if intent in REFUSAL_INTENTS:
        draft = refuse(intent, scheme_tag=scheme)
        final, issues = validate_response(
            draft, intent=intent, scheme_tag=scheme, prefer_groww=False, question=text
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "request_id=%s intent=%s latency_ms=%s validator=%s source_host=%s",
            request_id,
            intent,
            latency_ms,
            "pass" if not issues else "fixed:" + ",".join(issues),
            _host(final["source"]),
        )
        final["request_id"] = request_id
        return final

    # factual / process_howto
    result = retrieve(text, scheme_tag=scheme, intent=intent)
    if result.low_score:
        draft = not_in_corpus(scheme_tag=scheme)
        final, issues = validate_response(
            draft, intent=intent, scheme_tag=scheme, prefer_groww=True, question=text
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "request_id=%s intent=%s latency_ms=%s validator=%s source_host=%s low_score=1",
            request_id,
            intent,
            latency_ms,
            "pass" if not issues else "fixed:" + ",".join(issues),
            _host(final["source"]),
        )
        final["request_id"] = request_id
        return final

    gen = generate_answer(text, result.chunks, scheme_tag=scheme)
    cite_sbi = not _groww_has_field(result.chunks, text)
    if cite_sbi:
        # Prefer first non-Groww http URL when Groww lacks the field
        for c in result.chunks:
            meta = c.get("metadata") or {}
            if str(meta.get("publisher") or "").upper() == "GROWW":
                continue
            url = str(meta.get("url") or "")
            if url.startswith("http"):
                gen["source"] = url
                gen["last_updated_from_sources"] = str(meta.get("retrieved_on") or gen.get("last_updated_from_sources") or "")
                break
        gen["cite_sbi"] = True

    draft = {
        "intent": intent,
        "answer": gen["answer"],
        "source": gen["source"],
        "last_updated_from_sources": gen.get("last_updated_from_sources") or "",
        "cite_sbi": cite_sbi,
    }
    final, issues = validate_response(
        draft, intent=intent, scheme_tag=scheme, prefer_groww=not cite_sbi, question=text
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)
    logger.info(
        "request_id=%s intent=%s latency_ms=%s validator=%s source_host=%s chunks=%d",
        request_id,
        intent,
        latency_ms,
        "pass" if not issues else "fixed:" + ",".join(issues),
        _host(final["source"]),
        len(result.chunks),
    )
    final["request_id"] = request_id
    return final
