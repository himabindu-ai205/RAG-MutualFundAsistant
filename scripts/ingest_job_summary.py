"""Write GitHub Actions job summary from embed_manifest + corpus stamps."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "chroma" / "embed_manifest.json"
CHUNKS = ROOT / "data" / "chunks.jsonl"
GROWW_DIR = ROOT / "docs" / "corpus" / "groww"


def _groww_html_count() -> int:
    if not GROWW_DIR.is_dir():
        return 0
    return sum(1 for p in GROWW_DIR.glob("*.html") if p.is_file())


def _chunk_publisher_counts() -> dict[str, int]:
    if not CHUNKS.is_file():
        return {}
    counts: Counter[str] = Counter()
    with CHUNKS.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            pub = str(row.get("publisher") or "UNKNOWN").upper()
            counts[pub] += 1
    return dict(sorted(counts.items()))


def _retrieved_on_sample() -> str:
    if not CHUNKS.is_file():
        return "(no chunks.jsonl)"
    dates: Counter[str] = Counter()
    with CHUNKS.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            stamp = str(row.get("retrieved_on") or "").strip()
            if stamp:
                dates[stamp] += 1
    if not dates:
        return "(missing retrieved_on)"
    top = dates.most_common(3)
    return ", ".join(f"{d} ({n})" for d, n in top)


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        "## Daily ingest summary",
        "",
        f"- Finished (UTC): `{now}`",
        f"- Schedule target: **17:30 SGT** (09:30 UTC) via `.github/workflows/daily-ingest.yml`",
        f"- Groww HTML on disk: **{_groww_html_count()}**",
    ]

    if MANIFEST.is_file():
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        lines.extend(
            [
                f"- Collection: `{data.get('collection')}`",
                f"- Model: `{data.get('model')}`",
                f"- Total chunks: **{data.get('count')}**",
                f"- Groww chunks: **{data.get('groww_chunks')}**",
                f"- By publisher: `{json.dumps(data.get('by_publisher') or {}, sort_keys=True)}`",
            ]
        )
        groww = int(data.get("groww_chunks") or 0)
        if groww <= 0:
            lines.append("")
            lines.append("> **Warning:** Groww chunk count is 0 — index incomplete.")
    else:
        lines.append("- `embed_manifest.json`: **missing** (build may have failed)")

    pubs = _chunk_publisher_counts()
    if pubs:
        lines.append(f"- chunks.jsonl publishers: `{json.dumps(pubs)}`")
    lines.append(f"- `retrieved_on` (top): {_retrieved_on_sample()}")
    lines.extend(
        [
            "",
            "### Artifacts",
            "",
            "- Workflow uploads `data/chroma/` as artifact `chroma-index-<run_id>` (14-day retention).",
            "- Bot may commit Groww/shared HTML, `data/chunks.jsonl`, and `embed_manifest.json`.",
            "- Serving API does **not** live-browse; refresh local Chroma from the latest artifact (see README).",
        ]
    )

    text = "\n".join(lines) + "\n"
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        Path(summary_path).open("a", encoding="utf-8").write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
