"""Strip model artifacts from user-facing answer text."""

from __future__ import annotations

import re

# gpt-oss / Groq inline refs: 【1†L9-L10】, [1†L9-L10], stray †L9-L10
_INLINE_CITATION = re.compile(
    r"【[^】]*】|"  # fullwidth bracket citations
    r"\[\d+(?:†[^\]]*)?\]|"  # [1] or [1†L9-L10]
    r"†L\d+(?:-L\d+)?"  # orphan line refs
)


def strip_inline_citations(text: str) -> str:
    """Remove LLM footnote markers; collapse extra whitespace."""
    if not text:
        return text
    cleaned = _INLINE_CITATION.sub("", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()
