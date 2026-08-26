"""Shared serve config: schemes, citation URLs, disclaimer."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from src.ingest.registry import ROOT, load_sources

load_dotenv(ROOT / ".env")

DISCLAIMER = "Facts-only. No investment advice."
DISCLAIMER_FILE = ROOT / "disclaimer.txt"

AMFI_EDUCATION_URL = "https://www.amfiindia.com/investor"
SEBI_RISKOMETER_URL = "https://investor.sebi.gov.in/riskometer.html"
SBI_FACTSHEET_URL = "https://www.sbimf.com/factsheets/"
SBI_STATEMENT_URL = "https://www.sbimf.com/smart-statement"

ALLOWED_SOURCE_HOSTS = (
    "groww.in",
    "sbimf.com",
    "amfiindia.com",
    "sebi.gov.in",
)

# scheme_tag -> detection aliases (lowercased match)
SCHEME_ALIASES: dict[str, tuple[str, ...]] = {
    "sbi_large_cap": (
        "sbi large cap",
        "large cap",
        "bluechip",
        "blue chip",
        "sbi bluechip",
    ),
    "sbi_flexicap": (
        "sbi flexicap",
        "flexicap",
        "flexi cap",
        "flexi-cap",
    ),
    "sbi_elss": (
        "sbi elss",
        "elss",
        "tax saver",
        "long term equity",
        "magnum taxgain",
    ),
    "sbi_contra": (
        "sbi contra",
        "contra fund",
        "contra",
    ),
    "sbi_small_cap": (
        "sbi small cap",
        "small midcap",
        "small & midcap",
        "small and midcap",
        "small-midcap",
        "small cap",
    ),
}


def load_disclaimer() -> str:
    if DISCLAIMER_FILE.is_file():
        text = DISCLAIMER_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text
    return DISCLAIMER


def groww_url_by_scheme() -> dict[str, str]:
    out: dict[str, str] = {}
    for row in load_sources():
        if row.publisher.upper() == "GROWW" and row.scheme_tag:
            out[row.scheme_tag] = row.url
    return out


def groq_api_key() -> str | None:
    key = (os.getenv("GROQ_API_KEY") or "").strip()
    return key or None


def groq_model() -> str:
    return (os.getenv("GROQ_MODEL") or "openai/gpt-oss-120b").strip()


def groq_max_tokens() -> int:
    """Completion cap (includes gpt-oss reasoning). Default is the smallest that still yields ≤3 FAQ sentences."""
    raw = (os.getenv("GROQ_MAX_TOKENS") or "256").strip()
    try:
        return max(64, min(int(raw), 512))
    except ValueError:
        return 256


def groq_reasoning_effort() -> str:
    """gpt-oss-120b supports low|medium|high. Use low to minimize tokens/call."""
    raw = (os.getenv("GROQ_REASONING_EFFORT") or "low").strip().lower()
    return raw if raw in {"low", "medium", "high"} else "low"


def groq_context_chars() -> int:
    """Max chars per retrieved chunk sent to Groq (input token budget)."""
    raw = (os.getenv("GROQ_CONTEXT_CHARS") or "480").strip()
    try:
        return max(200, min(int(raw), 1800))
    except ValueError:
        return 480


def groq_context_chunks() -> int:
    """Max chunks included in the Groq prompt."""
    raw = (os.getenv("GROQ_CONTEXT_CHUNKS") or "3").strip()
    try:
        return max(1, min(int(raw), 6))
    except ValueError:
        return 3


def cors_origins() -> list[str]:
    """Browser origins allowed to call POST /chat (Vite local + CORS_ORIGINS)."""
    defaults = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    raw = (os.getenv("CORS_ORIGINS") or "").strip()
    extra = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for origin in defaults + extra:
        if origin not in seen:
            seen.add(origin)
            out.append(origin)
    return out


def cors_origin_regex() -> str | None:
    """Allow Vercel preview/production URLs unless CORS_ORIGIN_REGEX is set empty."""
    if "CORS_ORIGIN_REGEX" in os.environ:
        raw = os.environ["CORS_ORIGIN_REGEX"].strip()
        return raw or None
    return r"https://.*\.vercel\.app"


def chroma_dir() -> Path:
    raw = (os.getenv("CHROMA_DIR") or "").strip()
    return Path(raw) if raw else ROOT / "data" / "chroma"
