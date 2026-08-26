"""Phase 3.2 — Facts-only refusal messages (no retrieval for advice)."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.serve.config import (
    AMFI_EDUCATION_URL,
    SEBI_RISKOMETER_URL,
    SBI_FACTSHEET_URL,
    groww_url_by_scheme,
    load_disclaimer,
)


def _today() -> str:
    return date.today().isoformat()


def refuse(intent: str, *, scheme_tag: str | None = None) -> dict[str, Any]:
    """Return Architecture §12-shaped refusal payload (pre-validate)."""
    groww = groww_url_by_scheme()
    scheme_url = groww.get(scheme_tag or "", "")

    if intent == "advisory":
        answer = (
            "I cannot recommend whether to buy, sell, or hold any mutual fund. "
            "This assistant only reports published scheme facts from the corpus. "
            "For investor education, see AMFI’s investor resources."
        )
        source = AMFI_EDUCATION_URL
    elif intent == "comparative":
        answer = (
            "I cannot compare schemes or say which fund is better. "
            "Ask about one scheme’s published facts such as exit load, TER, or min SIP. "
            "AMFI publishes investor education on comparing funds carefully."
        )
        source = AMFI_EDUCATION_URL
    elif intent == "performance":
        answer = (
            "I do not compute or quote historical returns from Groww charts. "
            "For official performance figures, use the AMC factsheet page. "
            "You can also ask a factual question such as exit load or expense ratio."
        )
        source = SBI_FACTSHEET_URL
    elif intent == "pii":
        answer = (
            "Please do not share PAN, Aadhaar, account numbers, OTP, email, or phone. "
            "This assistant only answers published mutual-fund facts and does not need personal data. "
            "Rephrase your question without personal identifiers."
        )
        source = AMFI_EDUCATION_URL
    elif intent == "out_of_scope":
        answer = (
            "That question is outside this assistant’s scope (SBI Mutual Fund facts for five Groww-listed schemes). "
            "Try asking about exit load, expense ratio, min SIP, or ELSS lock-in. "
            "Investor education is available on AMFI’s site."
        )
        source = AMFI_EDUCATION_URL
    else:
        answer = (
            "I can only answer facts from the indexed Groww scheme pages and supporting SBI documents. "
            "Please ask about a published field such as exit load or TER."
        )
        source = scheme_url or AMFI_EDUCATION_URL

    return {
        "intent": intent,
        "answer": answer,
        "source": source,
        "last_updated_from_sources": _today(),
        "disclaimer": load_disclaimer(),
        "refused": True,
    }


def not_in_corpus(*, scheme_tag: str | None = None) -> dict[str, Any]:
    groww = groww_url_by_scheme()
    source = groww.get(scheme_tag or "") or SBI_FACTSHEET_URL
    if scheme_tag and scheme_tag in groww:
        answer = (
            "That detail was not found in the indexed corpus for this scheme. "
            "Check the Groww scheme page for the latest published facts. "
            "I do not invent numbers that are missing from the corpus."
        )
        source = groww[scheme_tag]
    else:
        answer = (
            "That detail was not found in the indexed corpus. "
            "Ask about an in-scope SBI scheme fact (exit load, TER, min SIP, lock-in) "
            "or see AMFI investor education."
        )
        source = AMFI_EDUCATION_URL
    return {
        "intent": "factual",
        "answer": answer,
        "source": source,
        "last_updated_from_sources": _today(),
        "disclaimer": load_disclaimer(),
        "refused": True,
        "not_in_corpus": True,
    }


def educational_riskometer() -> str:
    return SEBI_RISKOMETER_URL
