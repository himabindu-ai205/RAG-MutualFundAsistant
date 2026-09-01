"""Online pipeline: classify → refuse | retrieve → generate → validate."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any
from urllib.parse import urlparse

from src.serve.classify import Classification, classify
from src.serve.generate import generate_answer
from src.serve.refuse import not_in_corpus, refuse
from src.serve.retrieve import best_pdf_citation, groww_has_field, retrieve
from src.serve.validate import validate_response

logger = logging.getLogger(__name__)

REFUSAL_INTENTS = {"advisory", "comparative", "performance", "pii", "out_of_scope"}


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


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
    t_ret0 = time.perf_counter()
    result = retrieve(text, scheme_tag=scheme, intent=intent)
    retrieve_ms = int((time.perf_counter() - t_ret0) * 1000)
    if result.low_score:
        draft = not_in_corpus(scheme_tag=scheme)
        final, issues = validate_response(
            draft, intent=intent, scheme_tag=scheme, prefer_groww=True, question=text
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "request_id=%s intent=%s latency_ms=%s retrieve_ms=%s validator=%s source_host=%s low_score=1",
            request_id,
            intent,
            latency_ms,
            retrieve_ms,
            "pass" if not issues else "fixed:" + ",".join(issues),
            _host(final["source"]),
        )
        final["request_id"] = request_id
        return final

    t_gen0 = time.perf_counter()
    gen = generate_answer(text, result.chunks, scheme_tag=scheme)
    generate_ms = int((time.perf_counter() - t_gen0) * 1000)
    cite_sbi = not groww_has_field(result.chunks, text)
    if cite_sbi:
        url, retrieved_on = best_pdf_citation(result.chunks, text)
        if url:
            gen["source"] = url
            if retrieved_on:
                gen["last_updated_from_sources"] = retrieved_on
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
        "request_id=%s intent=%s latency_ms=%s retrieve_ms=%s generate_ms=%s validator=%s source_host=%s chunks=%d",
        request_id,
        intent,
        latency_ms,
        retrieve_ms,
        generate_ms,
        "pass" if not issues else "fixed:" + ",".join(issues),
        _host(final["source"]),
        len(result.chunks),
    )
    final["request_id"] = request_id
    return final
