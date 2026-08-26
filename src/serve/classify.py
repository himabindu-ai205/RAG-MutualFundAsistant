"""Phase 3.1 — Rules-first query classifier."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.serve.config import SCHEME_ALIASES

INTENTS = (
    "factual",
    "process_howto",
    "performance",
    "advisory",
    "comparative",
    "pii",
    "out_of_scope",
)

# Order matters: PII / advisory / comparative / performance before factual.
_PII_PATTERNS = [
    re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),  # PAN
    re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),  # Aadhaar-like
    re.compile(r"\b\d{9,18}\b"),  # account / long digit runs
    re.compile(r"\bOTP\b|\bone[\s-]*time\s+password\b", re.I),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b"),  # Indian mobile
]

_ADVISORY = re.compile(
    r"\b("
    r"should\s+i\s+(buy|sell|invest|switch|redeem|hold)|"
    r"is\s+it\s+(good|safe|worth)|"
    r"recommend|"
    r"advice|"
    r"advise|"
    r"best\s+fund\s+for\s+me|"
    r"portfolio\s+allocation|"
    r"where\s+should\s+i\s+invest"
    r")\b",
    re.I,
)

_COMPARATIVE = re.compile(
    r"\b("
    r"which\s+is\s+better|"
    r"better\s+than|"
    r"vs\.?|"
    r"versus|"
    r"compare|"
    r"comparison|"
    r"or\s+.+\s+which|"
    r"between\s+.+\s+and"
    r")\b",
    re.I,
)

_PERFORMANCE = re.compile(
    r"\b("
    r"\d[\s-]*(year|yr|month|mo)s?\s+return|"
    r"return(s)?\s+(over|in|for|of)|"
    r"cagr|"
    r"annualized|"
    r"how\s+much\s+(did|has)\s+.+\s+(return|gain|grow)|"
    r"past\s+performance|"
    r"nav\s+growth|"
    r"profit\s+in\s+\d|"
    r"xirr|"
    r"trailing\s+return"
    r")\b",
    re.I,
)

_PROCESS = re.compile(
    r"\b("
    r"how\s+(do|to|can)\s+i\s+(download|get|view|access|generate)|"
    r"smart\s+statement|"
    r"account\s+statement|"
    r"download\s+statement|"
    r"how\s+to\s+(redeem|switch|start\s+sip)\b|"
    r"kyc\s+process|"
    r"how\s+to\s+invest\s+in\s+elss"
    r")\b",
    re.I,
)

_FACTUAL_HINT = re.compile(
    r"\b("
    r"exit\s*load|"
    r"expense\s*ratio|\bTER\b|"
    r"min(?:imum)?\s+(SIP|investment|lumpsum)|"
    r"lock[\s-]*in|"
    r"riskometer|risk[\s-]*o?meter|"
    r"benchmark|"
    r"AUM|"
    r"category|"
    r"what\s+is|"
    r"what'?s\s+the"
    r")\b",
    re.I,
)

_IN_SCOPE_HINT = re.compile(
    r"\b("
    r"SBI|"
    r"Groww|"
    r"mutual\s+fund|"
    r"ELSS|"
    r"flexicap|flexi\s*cap|"
    r"large\s*cap|bluechip|"
    r"contra|"
    r"small\s*cap|small[\s-]*midcap|"
    r"SIP|"
    r"factsheet|statement|AMFI|SEBI|riskometer"
    r")\b",
    re.I,
)


@dataclass(frozen=True)
class Classification:
    intent: str
    scheme_tag: str | None = None
    has_pii: bool = False


def detect_scheme(question: str) -> str | None:
    q = question.lower()
    # Longer aliases first to avoid "cap" collisions
    scored: list[tuple[int, str]] = []
    for tag, aliases in SCHEME_ALIASES.items():
        for alias in aliases:
            if alias in q:
                scored.append((len(alias), tag))
                break
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]


def classify(question: str) -> Classification:
    text = (question or "").strip()
    if not text:
        return Classification(intent="out_of_scope")

    scheme = detect_scheme(text)
    has_pii = any(p.search(text) for p in _PII_PATTERNS)
    if has_pii:
        return Classification(intent="pii", scheme_tag=scheme, has_pii=True)

    if _ADVISORY.search(text):
        return Classification(intent="advisory", scheme_tag=scheme)
    if _COMPARATIVE.search(text):
        return Classification(intent="comparative", scheme_tag=scheme)
    if _PERFORMANCE.search(text):
        return Classification(intent="performance", scheme_tag=scheme)
    if _PROCESS.search(text):
        return Classification(intent="process_howto", scheme_tag=scheme)

    if _FACTUAL_HINT.search(text) or scheme:
        return Classification(intent="factual", scheme_tag=scheme)

    if _IN_SCOPE_HINT.search(text):
        return Classification(intent="factual", scheme_tag=scheme)

    return Classification(intent="out_of_scope", scheme_tag=scheme)
