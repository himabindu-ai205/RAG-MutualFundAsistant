"""Phase 3.5 — Response validator (Architecture §§7.7, 12, 16)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any
from urllib.parse import urlparse

from src.ingest.registry import host_allowed
from src.serve.config import (
    AMFI_EDUCATION_URL,
    SBI_FACTSHEET_URL,
    groww_url_by_scheme,
    load_disclaimer,
)
from src.serve.text_clean import strip_inline_citations
from src.serve.question_focus import question_focus, trim_unasked_facts

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PII_ECHO = [
    re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b"),
]
_RETURN_CLAIM = re.compile(
    r"\b("
    r"returned\s+\d|"
    r"\d+(\.\d+)?\s*%\s*(cagr|annualized|return)|"
    r"cagr\s+of|"
    r"gained\s+\d|"
    r"outperformed"
    r")\b",
    re.I,
)
_COMPARISON_CLAIM = re.compile(
    r"\b(better than|worse than|outperform|prefer .+ over)\b",
    re.I,
)
_LOCAL_PATH = re.compile(r"([A-Za-z]:\\|docs/corpus/|/home/|\\\\)", re.I)


def _truncate_sentences(text: str, max_sentences: int = 3) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return text
    parts = _SENTENCE_SPLIT.split(text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= max_sentences:
        return " ".join(parts)
    return " ".join(parts[:max_sentences])


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def validate_response(
    payload: dict[str, Any],
    *,
    intent: str,
    scheme_tag: str | None = None,
    prefer_groww: bool = True,
    question: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Enforce response contract. Returns (cleaned_payload, issues)."""
    issues: list[str] = []
    answer = _truncate_sentences(str(payload.get("answer") or ""))
    source = str(payload.get("source") or "").strip()
    last_updated = str(payload.get("last_updated_from_sources") or "").strip()
    disclaimer = load_disclaimer()
    groww = groww_url_by_scheme()

    # Strip any Source / Last updated the model may have embedded
    answer = re.sub(r"\s*Source:\s*\S+", "", answer, flags=re.I).strip()
    answer = re.sub(r"\s*Last updated from sources:\s*\S+", "", answer, flags=re.I).strip()
    answer = strip_inline_citations(answer)
    if question:
        answer = trim_unasked_facts(answer, question_focus(question))
    answer = _truncate_sentences(answer)

    if not answer:
        answer = "I can only report published facts from the indexed corpus."
        issues.append("empty_answer")

    # PII echo → refuse-style rewrite
    if any(p.search(answer) for p in _PII_ECHO):
        answer = (
            "Please do not share personal identifiers. "
            "This assistant only answers published mutual-fund facts."
        )
        source = AMFI_EDUCATION_URL
        issues.append("pii_echo")

    # Invented returns / comparisons on factual path → factsheet refusal
    if intent in {"factual", "process_howto"} and (
        _RETURN_CLAIM.search(answer) or _COMPARISON_CLAIM.search(answer)
    ):
        answer = (
            "I do not compute or compare returns. "
            "For official performance figures, use the AMC factsheet. "
            "Ask a factual question such as exit load or expense ratio instead."
        )
        source = SBI_FACTSHEET_URL
        issues.append("blocked_return_or_comparison")

    # Local paths never as citation
    if _LOCAL_PATH.search(source) or source.startswith("/") or "\\" in source:
        issues.append("local_path_source")
        if prefer_groww and scheme_tag and scheme_tag in groww:
            source = groww[scheme_tag]
        else:
            source = AMFI_EDUCATION_URL

    if not source.startswith("http") or not host_allowed(source):
        issues.append("bad_source_host")
        if prefer_groww and scheme_tag and scheme_tag in groww:
            source = groww[scheme_tag]
        elif intent in {"advisory", "comparative", "pii", "out_of_scope"}:
            source = AMFI_EDUCATION_URL
        elif intent == "performance":
            source = SBI_FACTSHEET_URL
        elif scheme_tag and scheme_tag in groww:
            source = groww[scheme_tag]
        else:
            source = AMFI_EDUCATION_URL

    # Factual scheme Qs: prefer groww.in when available
    if prefer_groww and intent in {"factual", "process_howto"} and scheme_tag and scheme_tag in groww:
        if _host(source) != "groww.in" and not payload.get("not_in_corpus"):
            # Keep SBI only when caller marked groww_lacks_field
            if not payload.get("cite_sbi"):
                source = groww[scheme_tag]
                issues.append("forced_groww_source")

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", last_updated):
        last_updated = date.today().isoformat()
        issues.append("missing_last_updated")

    # Ensure ≤3 sentences after rewrites
    answer = _truncate_sentences(answer, 3)

    out = {
        "intent": intent,
        "answer": answer,
        "source": source,
        "last_updated_from_sources": last_updated,
        "disclaimer": disclaimer,
    }
    return out, issues
