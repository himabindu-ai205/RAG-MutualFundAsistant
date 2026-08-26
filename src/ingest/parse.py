"""Phase 2.2 — Parse and normalize corpus documents.

Groww HTML first (primary), then SBI PDFs, then shared official HTML.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

from src.ingest.registry import ROOT, SourceRow, load_sources

logger = logging.getLogger(__name__)

# Phase 1.5/1.6 confirmed aliases (applied for detection/normalization text only).
SAFE_ALIASES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bbluechip\b", re.I), "Large Cap"),
    (re.compile(r"\bsbi\s+bluechip\s+fund\b", re.I), "SBI Large Cap Fund"),
    (re.compile(r"\blong[\s-]*term[\s-]*equity\b", re.I), "ELSS Tax Saver"),
    (re.compile(r"\bmagnum\s+taxgain\b", re.I), "ELSS Tax Saver"),
    (re.compile(r"\bsmall\s*&\s*mid\s*cap\b", re.I), "Small Cap"),
    (re.compile(r"\bsmall[\s-]*midcap\b", re.I), "Small Cap"),
    (re.compile(r"\bsmall\s+and\s+midcap\b", re.I), "Small Cap"),
]

DROP_LINE_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"^compare similar funds$",
        r"^people also",
        r"^download the app$",
        r"^©\s*\d{4}",
        r"^version:\s*\d",
        r"^open demat",
        r"^brokerage calculator$",
        r"^sip calculator$",
        r"^understand terms$",
        r"^also manages these schemes$",
        r"^view details$",
        r"^home>\s*mutual funds",
        r"^vaishnavi tech park",
    ]
]


@dataclass
class ParsedDocument:
    source_id: str
    url: str
    publisher: str
    doc_type: str
    scheme: str
    scheme_tag: str
    local_path: str
    retrieved_on: str
    priority: int
    text: str
    facts: dict[str, str] = field(default_factory=dict)
    sections: dict[str, str] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.text)


class ParseError(RuntimeError):
    """Raised when a required document cannot be parsed."""


def normalize_whitespace(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def apply_safe_aliases(text: str) -> str:
    """Normalize known former names in free text (citations stay on registry URLs)."""
    out = text
    for pattern, replacement in SAFE_ALIASES:
        out = pattern.sub(replacement, out)
    return out


def _clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if any(p.search(line) for p in DROP_LINE_PATTERNS):
            continue
        lines.append(line)
    return lines


def _strip_html_noise(soup: BeautifulSoup) -> None:
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    for tag in soup.find_all(["footer", "nav"]):
        tag.decompose()
    for tag in soup.find_all(attrs={"role": re.compile(r"navigation|banner|contentinfo", re.I)}):
        tag.decompose()


def _extract_groww_exit_load(lines: list[str], joined: str) -> str | None:
    """Prefer the current exit-load line (after stamp-duty heading), not truncated history."""
    # Current block: "Exit load, stamp duty and tax" → "Exit load" → value (sentence or Nil)
    for i, line in enumerate(lines):
        if not re.search(r"exit\s*load,\s*stamp\s*duty", line, re.I):
            continue
        for j in range(i + 1, min(i + 8, len(lines))):
            val = lines[j].strip()
            if re.fullmatch(r"exit\s*load", val, re.I):
                continue
            if re.fullmatch(r"nil|nil\.|n/?a|--", val, re.I):
                return "Nil"
            if re.match(r"exit\s*load\s+of\b", val, re.I):
                return normalize_whitespace(val).rstrip(".;")
            if re.match(r"stamp\s*duty", val, re.I):
                break

    candidates: list[str] = []
    for i, line in enumerate(lines):
        if re.match(r"exit\s*load\s+of\b", line, re.I):
            candidates.append(normalize_whitespace(line).rstrip(".;"))
        elif re.fullmatch(r"nil|nil\.", line, re.I) and i > 0:
            prev = lines[i - 1]
            if re.search(r"exit\s*load", prev, re.I):
                candidates.append("Nil")
    if candidates:
        # Prefer detailed tiered sentences over short / Nil when both appear
        non_nil = [c for c in candidates if c.lower() != "nil"]
        if non_nil:
            non_nil.sort(key=len, reverse=True)
            return non_nil[0]
        return "Nil"

    m = re.search(
        r"(Exit load of .+?(?:days|months|year|allotment)\.?)",
        joined,
        re.I | re.DOTALL,
    )
    if m:
        return normalize_whitespace(m.group(1)).rstrip(".;")
    if re.search(r"exit\s*load\s*[:\-]?\s*nil\b", joined, re.I):
        return "Nil"
    return None


def _extract_groww_facts(lines: list[str], joined: str) -> dict[str, str]:
    facts: dict[str, str] = {}

    def next_value(label: str) -> str | None:
        for i, line in enumerate(lines):
            if line.lower() == label.lower() and i + 1 < len(lines):
                return lines[i + 1]
        return None

    expense = next_value("Expense ratio")
    if expense and re.search(r"\d", expense):
        facts["expense_ratio"] = expense

    sip = next_value("Min. for SIP")
    if sip and re.search(r"\d", sip):
        facts["min_sip"] = sip

    aum = next_value("Fund size (AUM)")
    if aum and re.search(r"\d", aum):
        facts["aum"] = aum

    m = re.search(
        r"Minimum SIP Investment is set to\s*([₹Rs.\s0-9,]+)",
        joined,
        re.I,
    )
    if m:
        facts.setdefault("min_sip", m.group(1).strip())

    m = re.search(
        r"Minimum Lumpsum Investment is\s*([₹Rs.\s0-9,]+)",
        joined,
        re.I,
    )
    if m:
        facts["min_lumpsum"] = m.group(1).strip().rstrip(".")

    exit_load = _extract_groww_exit_load(lines, joined)
    if exit_load:
        facts["exit_load"] = exit_load

    for line in lines:
        if re.search(r"3Y\s*Lock-in|lock[\s-]*in", line, re.I) and len(line) < 80:
            cleaned = re.sub(r"[\x00-\x1f]+", " ", line)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            # Prefer product badge over glossary noise
            if "fee payable" in cleaned.lower() or "capital gains" in cleaned.lower():
                continue
            facts["lock_in"] = cleaned
            break
    if "lock_in" not in facts:
        m = re.search(
            r"(ELSS[^\n]{0,20}3Y\s*Lock-in|3[\s-]*year[s]?\s+lock[\s-]*in[^\n]{0,80})",
            joined,
            re.I,
        )
        if m:
            facts["lock_in"] = normalize_whitespace(m.group(1))

    m = re.search(
        r"Latest NAV as of\s*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})\s+is\s*(₹[\d,]+(?:\.\d+)?)",
        joined,
        re.I,
    )
    if m:
        facts["nav"] = f"{m.group(2)} (as of {m.group(1)})"
    else:
        m = re.search(
            r"NAV:\s*([0-9]{1,2}\s+[A-Za-z]{3,9}\s*'?[0-9]{2,4})\s*(₹[\d,]+(?:\.\d+)?)",
            joined,
            re.I,
        )
        if m:
            facts["nav"] = f"{m.group(2)} (as of {m.group(1)})"

    m = re.search(r"\b(Very High Risk|High Risk|Moderately High Risk|Moderate Risk)\b", joined, re.I)
    if m:
        facts["riskometer"] = m.group(1).strip()

    m = re.search(r"Fund benchmark\s*([^\n]+)", joined, re.I)
    if m:
        bench = m.group(1).strip()
        if len(bench) < 120:
            facts["benchmark"] = bench

    m = re.search(r"\b(Equity\s*[•·|-]\s*[A-Za-z &]+|Flexi Cap|Large Cap|Small Cap|ELSS|Contra)\b", joined)
    if m:
        facts.setdefault("category", m.group(1).strip())

    return facts


def _groww_main_text(lines: list[str]) -> str:
    """Prefer About / objective / exit-load regions; drop long fund-manager lists."""
    keep: list[str] = []
    skip_blocks = False
    for line in lines:
        low = line.lower()
        if low.startswith("also manages these schemes") or low.startswith("compare similar funds"):
            skip_blocks = True
            continue
        if skip_blocks and (
            low.startswith("about ")
            or low.startswith("investment objective")
            or low.startswith("exit load")
            or low.startswith("fund house")
        ):
            skip_blocks = False
        if skip_blocks:
            continue
        # Drop endless similar-fund return rows
        if re.match(r"^[A-Za-z].*(Direct Growth|\+[\d.]+%)$", line) and "SBI" not in line:
            if "fund" in low and "sbi" not in low:
                continue
        keep.append(line)
    return "\n".join(keep)


def parse_groww_html(row: SourceRow, html: str) -> ParsedDocument:
    soup = BeautifulSoup(html, "html.parser")
    _strip_html_noise(soup)
    raw_text = soup.get_text("\n", strip=True)
    lines = _clean_lines(raw_text)
    body = _groww_main_text(lines)
    body = apply_safe_aliases(normalize_whitespace(body))
    facts = _extract_groww_facts(lines, body)

    # Structured facts block for higher-quality chunks later.
    fact_lines = [f"{k.replace('_', ' ').title()}: {v}" for k, v in facts.items()]
    if fact_lines:
        body = "Scheme facts (from Groww page):\n" + "\n".join(fact_lines) + "\n\n" + body

    sections: dict[str, str] = {"full": body}
    if facts.get("exit_load"):
        sections["exit_load"] = facts["exit_load"]
    if facts.get("expense_ratio"):
        sections["expense_ratio"] = facts["expense_ratio"]
    if facts.get("min_sip") or facts.get("min_lumpsum"):
        sections["minimum_investment"] = "; ".join(
            f"{k}: {facts[k]}" for k in ("min_sip", "min_lumpsum") if k in facts
        )
    if facts.get("lock_in"):
        sections["lock_in"] = facts["lock_in"]
    if facts.get("riskometer") or facts.get("benchmark"):
        sections["risk_benchmark"] = "; ".join(
            f"{k}: {facts[k]}" for k in ("riskometer", "benchmark") if k in facts
        )

    return ParsedDocument(
        source_id=row.source_id,
        url=row.url,
        publisher=row.publisher,
        doc_type=row.doc_type,
        scheme=row.scheme,
        scheme_tag=row.scheme_tag,
        local_path=row.local_path,
        retrieved_on=row.retrieved_on,
        priority=row.priority,
        text=body,
        facts=facts,
        sections=sections,
    )


HUB_SOURCE_IDS = {
    "sbi-home",
    "sbi-sid-kim-hub",
    "sbi-factsheets-hub",
    "sbi-smart-statement",
    "sbi-ter",
}

# SID / long PDF: cut branch-office and collector lists before windowing.
_PDF_TAIL_MARKERS = [
    re.compile(r"\n\s*(?:list of|official)\s+(?:collection\s+)?centres?\b", re.I),
    re.compile(r"\n\s*investor\s+service\s+centres?\b", re.I),
    re.compile(r"\n\s*ASANSOL\s*:", re.I),
    re.compile(r"\n\s*AGRA\s*:", re.I),
    re.compile(r"\n\s*addresses?\s+of\s+(?:the\s+)?(?:registrar|collecting)", re.I),
]


def parse_shared_html(row: SourceRow, html: str) -> ParsedDocument:
    soup = BeautifulSoup(html, "html.parser")
    _strip_html_noise(soup)
    # Prefer main/article if present
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text("\n", strip=True)
    lines = _clean_lines(text)
    body = apply_safe_aliases(normalize_whitespace("\n".join(lines)))
    # Soft cap huge marketing pages
    if len(body) > 80_000:
        body = body[:80_000] + "\n..."

    is_hub = row.source_id in HUB_SOURCE_IDS or row.doc_type in {
        "factsheet",
        "statement_guide",
        "TER",
        "FAQ",
    }
    facts: dict[str, str] = {}
    sections: dict[str, str] = {"full": body}
    doc_type = row.doc_type
    if is_hub:
        facts["corpus_role"] = "hub"
        # Thin hubs are navigation pages, not scheme factsheets.
        doc_type = "hub" if row.doc_type in {"factsheet", "FAQ", "statement_guide", "TER"} else row.doc_type
        preview = body[:1500].strip()
        sections = {
            "full": preview,
            "hub": (
                f"Official hub page ({row.doc_type}): {row.url}\n"
                f"This page is a navigation/index hub, not a full scheme factsheet or SID.\n"
                f"Preview:\n{preview}"
            ),
        }

    return ParsedDocument(
        source_id=row.source_id,
        url=row.url,
        publisher=row.publisher,
        doc_type=doc_type,
        scheme=row.scheme,
        scheme_tag=row.scheme_tag,
        local_path=row.local_path,
        retrieved_on=row.retrieved_on,
        priority=row.priority,
        text=body if not is_hub else sections["hub"],
        facts=facts,
        sections=sections,
    )


def _tables_as_text(page) -> str:
    parts: list[str] = []
    try:
        tables = page.extract_tables() or []
    except Exception:  # noqa: BLE001
        return ""
    for table in tables:
        for row in table:
            cells = [normalize_whitespace(c or "") for c in row]
            cells = [c for c in cells if c]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def parse_pdf(row: SourceRow, path: Path) -> ParsedDocument:
    pages_text: list[str] = []
    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            # Tables only on the first few pages (KIM is short; SID front-matter).
            max_table_pages = 12 if row.doc_type == "KIM" else 6
            for i, page in enumerate(pdf.pages):
                t = page.extract_text() or ""
                chunk = t
                if i < max_table_pages:
                    tables = _tables_as_text(page)
                    if tables:
                        chunk = (t + "\n" + tables).strip()
                if chunk.strip():
                    pages_text.append(chunk.strip())
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdfplumber failed for %s (%s); trying pypdf", row.source_id, exc)
        pages_text = []

    if not pages_text:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                pages_text.append(t.strip())

    body = apply_safe_aliases(normalize_whitespace("\n\n".join(pages_text)))
    if not body:
        raise ParseError(f"No text extracted from PDF {row.source_id}: {path}")

    body = _trim_pdf_tail(body)
    sections = _split_pdf_sections(body)
    facts = _extract_pdf_facts(body)
    # Prefer section snippets for facts when available
    for key in ("exit_load", "lock_in", "expense_ratio", "minimum_investment", "benchmark"):
        if key in sections and key not in facts:
            facts[key] = normalize_whitespace(sections[key][:400])
    return ParsedDocument(
        source_id=row.source_id,
        url=row.url,
        publisher=row.publisher,
        doc_type=row.doc_type,
        scheme=row.scheme,
        scheme_tag=row.scheme_tag,
        local_path=row.local_path,
        retrieved_on=row.retrieved_on,
        priority=row.priority,
        text=body,
        facts=facts,
        sections=sections or {"full": body},
    )


_SECTION_HEADERS = [
    ("investment objective", "investment_objective"),
    ("asset allocation pattern", "asset_allocation"),
    ("asset allocation", "asset_allocation"),
    ("exit load", "exit_load"),
    ("load structure", "exit_load"),
    ("recurring expenses", "expense_ratio"),
    ("expense ratio", "expense_ratio"),
    ("fees and expenses", "expense_ratio"),
    ("total expense ratio", "expense_ratio"),
    ("minimum application amount", "minimum_investment"),
    ("minimum application", "minimum_investment"),
    ("minimum investment", "minimum_investment"),
    ("minimum sip", "minimum_investment"),
    ("lock-in period", "lock_in"),
    ("lock-in", "lock_in"),
    ("lock in", "lock_in"),
    ("scheme benchmark", "benchmark"),
    ("benchmark", "benchmark"),
    ("risk-o-meter", "riskometer"),
    ("riskometer", "riskometer"),
    ("product labelling", "riskometer"),
    ("risk factors", "risk_factors"),
]


def _trim_pdf_tail(text: str) -> str:
    """Drop ISC / branch-address appendices that drown SID embeddings."""
    min_keep = max(50_000, int(len(text) * 0.35))
    cut = len(text)
    for pat in _PDF_TAIL_MARKERS:
        m = pat.search(text)
        if m and m.start() >= min_keep:
            cut = min(cut, m.start())
    # Hard cap SIDs after substantial front-matter
    if cut > 120_000:
        cut = 120_000
    trimmed = text[:cut].strip()
    if len(trimmed) < len(text):
        logger.info("Trimmed PDF tail: %d → %d chars", len(text), len(trimmed))
    return trimmed


def _split_pdf_sections(text: str) -> dict[str, str]:
    lower = text.lower()
    hits: list[tuple[int, str]] = []
    for needle, key in _SECTION_HEADERS:
        start = 0
        while True:
            idx = lower.find(needle, start)
            if idx < 0:
                break
            # Prefer line-ish starts
            if idx == 0 or text[idx - 1] in "\n\r \t|:":
                hits.append((idx, key))
            start = idx + len(needle)
    if not hits:
        return {"full": text}
    hits.sort(key=lambda x: x[0])
    # Dedupe same key keeping first
    seen: set[str] = set()
    unique: list[tuple[int, str]] = []
    for idx, key in hits:
        if key in seen:
            continue
        seen.add(key)
        unique.append((idx, key))
    sections: dict[str, str] = {"full": text}
    for i, (idx, key) in enumerate(unique):
        # Bound section: next header or modest char window
        next_idx = unique[i + 1][0] if i + 1 < len(unique) else min(len(text), idx + 3500)
        end = min(next_idx, idx + 3500)
        snippet = text[idx:end].strip()
        if snippet and len(snippet) >= 20:
            sections[key] = snippet[:4000]
    return sections


def _extract_pdf_facts(text: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    m = re.search(r"(exit load[^\n]{0,200})", text, re.I)
    if m:
        facts["exit_load"] = normalize_whitespace(m.group(1))
    m = re.search(r"(lock[\s-]*in[^\n]{0,160})", text, re.I)
    if m:
        facts["lock_in"] = normalize_whitespace(m.group(1))
    m = re.search(r"(minimum (?:application|investment|sip)[^\n]{0,160})", text, re.I)
    if m:
        facts["minimum_investment"] = normalize_whitespace(m.group(1))
    m = re.search(r"(benchmark[^\n]{0,120})", text, re.I)
    if m:
        facts["benchmark"] = normalize_whitespace(m.group(1))
    return facts


def _is_pdf_row(row: SourceRow) -> bool:
    return row.doc_type in {"KIM", "SID"} or row.local_path.lower().endswith(".pdf")


def parse_source(row: SourceRow, *, root: Path = ROOT) -> ParsedDocument:
    path = row.local_file(root)
    if not path.is_file():
        raise ParseError(f"Missing local file for {row.source_id}: {path}")

    if row.publisher.upper() == "GROWW" or row.doc_type == "groww_scheme":
        html = path.read_text(encoding="utf-8", errors="ignore")
        return parse_groww_html(row, html)

    if _is_pdf_row(row):
        return parse_pdf(row, path)

    # Shared / official HTML
    raw = path.read_bytes()
    html = raw.decode("utf-8", errors="ignore")
    return parse_shared_html(row, html)


def parse_all(
    rows: list[SourceRow] | None = None,
    *,
    root: Path = ROOT,
    skip_missing: bool = False,
) -> list[ParsedDocument]:
    """Parse registry in Groww-first order (priority ascending, Groww before others)."""
    source_rows = list(rows or load_sources())
    source_rows.sort(key=lambda r: (r.priority, 0 if r.publisher.upper() == "GROWW" else 1, r.source_id))

    docs: list[ParsedDocument] = []
    for row in source_rows:
        try:
            doc = parse_source(row, root=root)
        except ParseError as exc:
            if skip_missing:
                logger.warning("%s", exc)
                continue
            raise
        if not doc.text.strip():
            logger.warning("Empty parse for %s", row.source_id)
            continue
        docs.append(doc)
        logger.info(
            "Parsed %s (%s) chars=%d facts=%d sections=%d",
            doc.source_id,
            doc.publisher,
            doc.char_count,
            len(doc.facts),
            len(doc.sections),
        )
    return docs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 2.2 corpus parser")
    parser.add_argument("--skip-missing", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "--source-id",
        action="append",
        default=[],
        help="Only parse these source_id values (repeatable)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    rows = load_sources()
    if args.source_id:
        wanted = set(args.source_id)
        rows = [r for r in rows if r.source_id in wanted]

    try:
        docs = parse_all(rows, skip_missing=args.skip_missing)
    except ParseError as exc:
        logger.error("%s", exc)
        return 1

    by_pub: dict[str, int] = {}
    for d in docs:
        by_pub[d.publisher] = by_pub.get(d.publisher, 0) + 1

    groww_facts = sum(1 for d in docs if d.publisher.upper() == "GROWW" and d.facts)
    print(
        f"Parsed documents: {len(docs)} | by publisher: {by_pub} | "
        f"Groww with extracted facts: {groww_facts}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
