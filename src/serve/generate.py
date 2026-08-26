"""Phase 3.4 — Constrained Groq generator (chunks-only context)."""

from __future__ import annotations

import logging
import re
from typing import Any

from src.serve.config import (
    groq_api_key,
    groq_context_chars,
    groq_context_chunks,
    groq_max_tokens,
    groq_model,
    groq_reasoning_effort,
)
from src.serve.retrieve import choose_citation_url

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Facts-only SBI mutual fund FAQ (Groww-primary).
Use CONTEXT only. Prefer GROWW/priority=1. Quote published Latest NAV if present.
No advice, comparisons, return math, or invented numbers. ≤3 short sentences.
No Source:/Last updated lines. No file paths."""


def _prefer_compact_chunks(chunks: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Prefer Scheme Facts / short field sections to cut input tokens."""

    def rank(ch: dict[str, Any]) -> tuple[int, int]:
        meta = ch.get("metadata") or {}
        section = str(meta.get("section_title") or "").lower()
        pri = int(meta.get("priority") or 99)
        if "fact" in section:
            tip = 0
        elif section in {
            "exit load",
            "lock-in",
            "expense ratio",
            "minimum investment",
            "riskometer",
            "benchmark",
            "hub overview",
        }:
            tip = 1
        elif section == "full_document":
            tip = 3
        else:
            tip = 2
        return (tip, pri)

    ordered = sorted(chunks, key=rank)
    return ordered[:limit]


def _format_context(chunks: list[dict[str, Any]]) -> str:
    char_cap = groq_context_chars()
    parts: list[str] = []
    for i, ch in enumerate(chunks, 1):
        meta = ch.get("metadata") or {}
        header = (
            f"[{i}] pub={meta.get('publisher')} pri={meta.get('priority')} "
            f"scheme={meta.get('scheme_tag')} section={meta.get('section_title')}"
        )
        text = (ch.get("text") or "")[:char_cap]
        parts.append(f"{header}\n{text}")
    return "\n\n".join(parts)


def generate_answer(
    question: str,
    chunks: list[dict[str, Any]],
    *,
    scheme_tag: str | None = None,
) -> dict[str, Any]:
    """Call Groq with retrieved chunks only. Returns draft answer + preferred citation."""
    url, retrieved_on = choose_citation_url(chunks, scheme_tag=scheme_tag)
    compact = _prefer_compact_chunks(chunks, groq_context_chunks())
    context = _format_context(compact)
    user_prompt = (
        f"QUESTION: {question}\n\n"
        f"CONTEXT:\n{context}\n\n"
        "Answer in ≤3 sentences using only CONTEXT."
    )

    key = groq_api_key()
    if not key:
        answer = _extractive_fallback(question, chunks)
        return {
            "answer": answer,
            "source": url,
            "last_updated_from_sources": retrieved_on,
            "model": "extractive-fallback",
        }

    max_out = groq_max_tokens()
    effort = groq_reasoning_effort()
    try:
        from groq import Groq

        client = Groq(api_key=key)
        completion = client.chat.completions.create(
            model=groq_model(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_completion_tokens=max_out,
            reasoning_effort=effort,
            include_reasoning=False,
        )
        answer = (completion.choices[0].message.content or "").strip()
        usage = getattr(completion, "usage", None)
        if usage is not None:
            logger.info(
                "groq_usage model=%s prompt=%s completion=%s total=%s max_completion=%s effort=%s",
                groq_model(),
                getattr(usage, "prompt_tokens", "?"),
                getattr(usage, "completion_tokens", "?"),
                getattr(usage, "total_tokens", "?"),
                max_out,
                effort,
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("Groq generation failed: %s", exc)
        answer = _extractive_fallback(question, chunks)

    answer = _strip_meta_lines(answer)
    return {
        "answer": answer,
        "source": url,
        "last_updated_from_sources": retrieved_on,
        "model": groq_model(),
    }


def _strip_meta_lines(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if re.match(r"^\s*source\s*:", line, re.I):
            continue
        if re.match(r"^\s*last\s+updated", line, re.I):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _extractive_fallback(question: str, chunks: list[dict[str, Any]]) -> str:
    """Simple fact pull when Groq is unavailable — prefers Groww Scheme Facts."""
    q = question.lower()
    groww_facts = [
        c
        for c in chunks
        if str((c.get("metadata") or {}).get("publisher") or "").upper() == "GROWW"
        and "fact" in str((c.get("metadata") or {}).get("section_title") or "").lower()
    ]
    pool = groww_facts or chunks
    if not pool:
        return "That detail was not found in the indexed corpus."

    text = "\n".join(c.get("text") or "" for c in pool)
    patterns: list[tuple[str, re.Pattern[str]]] = [
        ("nav", re.compile(r"(?:Latest NAV|Nav):\s*(.+?)(?:\n|$)", re.I)),
        ("nav", re.compile(r"Latest NAV as of\s*([^\n.]+?\s+is\s*₹[\d,.]+)", re.I)),
        ("exit load", re.compile(r"Exit Load:\s*(.+)", re.I)),
        ("expense", re.compile(r"Expense Ratio:\s*(.+)", re.I)),
        ("sip", re.compile(r"Min Sip:\s*(.+)", re.I)),
        ("lock", re.compile(r"Lock In:\s*(.+)", re.I)),
        ("risk", re.compile(r"Riskometer:\s*(.+)", re.I)),
    ]
    for key, pat in patterns:
        if key == "nav" and not re.search(r"\bnav\b", q):
            continue
        if key != "nav" and key not in q:
            continue
        m = pat.search(text)
        if m:
            val = m.group(1).strip().split("\n")[0]
            if key == "nav":
                return f"According to the indexed Groww page, the latest NAV is {val}."
            return f"According to the indexed Groww scheme facts, {key} is recorded as: {val}."
    snippet = re.sub(r"\s+", " ", text)[:220].strip()
    return f"From the indexed corpus: {snippet}"
