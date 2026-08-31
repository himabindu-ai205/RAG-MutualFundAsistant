"""Detect which FAQ field(s) a question asks for — used to keep answers on-topic."""

from __future__ import annotations

import re
from typing import Literal

Focus = Literal[
    "plan_options",
    "nav",
    "exit_load",
    "ter",
    "sip",
    "lock_in",
    "riskometer",
    "benchmark",
    "aum",
    "category",
    "general",
]

_PLAN_OPTIONS = re.compile(
    r"\b("
    r"plan\s*options?|"
    r"which\s+plans?|"
    r"what\s+plans?|"
    r"plan\s+types?|"
    r"direct\s+or\s+regular|"
    r"regular\s+plan|"
    r"idcw|"
    r"dividend\s+option|"
    r"growth\s+option"
    r")\b",
    re.I,
)
_NAV = re.compile(r"\bnav\b|net\s+asset\s+value", re.I)
_EXIT_LOAD = re.compile(r"exit\s*load", re.I)
_TER = re.compile(r"\bter\b|expense\s*ratio", re.I)
_SIP = re.compile(r"\bsip\b|min(?:imum)?\s+(?:for\s+)?sip|lumpsum|lump\s*sum|minimum\s+investment", re.I)
_LOCK_IN = re.compile(r"lock[\s-]*in", re.I)
_RISK = re.compile(r"riskometer|risk[\s-]*o?meter", re.I)
_BENCHMARK = re.compile(r"\bbenchmark\b", re.I)
_AUM = re.compile(r"\baum\b|fund\s+size|assets\s+under", re.I)
_CATEGORY = re.compile(r"\bcategory\b|fund\s+type|scheme\s+type", re.I)


def question_focus(question: str) -> Focus:
    """Single primary focus for factual FAQ questions."""
    q = (question or "").strip()
    if _PLAN_OPTIONS.search(q):
        return "plan_options"
    if _NAV.search(q):
        return "nav"
    if _EXIT_LOAD.search(q):
        return "exit_load"
    if _TER.search(q):
        return "ter"
    if _SIP.search(q):
        return "sip"
    if _LOCK_IN.search(q):
        return "lock_in"
    if _RISK.search(q):
        return "riskometer"
    if _BENCHMARK.search(q):
        return "benchmark"
    if _AUM.search(q):
        return "aum"
    if _CATEGORY.search(q):
        return "category"
    return "general"


def focus_instruction(focus: Focus) -> str:
    """Extra generator instruction for the detected focus."""
    common = "Answer ONLY what the question asks. Do not add other scheme facts."
    mapping: dict[Focus, str] = {
        "plan_options": (
            f"{common} State plan/option names only (e.g. Direct Plan – Growth). "
            "Do NOT include NAV, expense ratio, min SIP, lumpsum, exit load, benchmark, or AUM."
        ),
        "nav": f"{common} Give latest NAV (and as-of date if in CONTEXT). No other fields.",
        "exit_load": f"{common} Give exit load only. No other fields.",
        "ter": f"{common} Give expense ratio / TER only. No other fields.",
        "sip": f"{common} Give minimum SIP and/or lumpsum only if asked. No other fields.",
        "lock_in": f"{common} Give lock-in period only. No other fields.",
        "riskometer": f"{common} Give riskometer only. No other fields.",
        "benchmark": f"{common} Give benchmark only. No other fields.",
        "aum": f"{common} Give AUM / fund size only. No other fields.",
        "category": f"{common} Give fund category only. No other fields.",
        "general": common,
    }
    return mapping[focus]


def trim_unasked_facts(answer: str, focus: Focus) -> str:
    """Remove common extra facts when the question asked for something narrow."""
    if focus != "plan_options" or not answer:
        return answer
    text = answer.strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    kept: list[str] = []
    for part in parts:
        low = part.lower()
        if any(
            k in low
            for k in (
                "minimum lump",
                "min sip",
                "minimum sip",
                "expense ratio",
                "latest nav",
                " nav ",
                "exit load",
                "benchmark",
                "riskometer",
                " aum",
            )
        ):
            if not _PLAN_OPTIONS.search(part):
                continue
        kept.append(part)
    text = " ".join(kept) if kept else text
    return re.sub(r"\s{2,}", " ", text).strip(" .")
