"""Inspect Chroma embeddings and run example retrieval.

Examples:
  python scripts/inspect_retrieval.py
  python scripts/inspect_retrieval.py --query "Exit load of SBI Flexicap?"
  python scripts/inspect_retrieval.py --show-vectors --chunk-id groww-flexicap#facts#0
  python scripts/inspect_retrieval.py --list-facts
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest.embed import (
    COLLECTION_NAME,
    DEFAULT_CHROMA_DIR,
    DEFAULT_MODEL,
    EmbedConfig,
    query_chunks,
)
from src.serve.classify import classify
from src.serve.retrieve import retrieve

EXAMPLE_QUERIES = [
    "Exit load of SBI Flexicap?",
    "What is the ELSS lock-in period?",
    "Minimum SIP for SBI Large Cap?",
    "Expense ratio of SBI Contra Fund?",
    "Latest NAV of SBI Small Cap?",
]


def _client(chroma_dir: Path):
    import chromadb
    from chromadb.config import Settings

    return chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=Settings(anonymized_telemetry=False),
    )


def _collection(chroma_dir: Path, name: str = COLLECTION_NAME):
    return _client(chroma_dir).get_collection(name)


def _preview(text: str, n: int = 160) -> str:
    one = " ".join((text or "").split())
    return one if len(one) <= n else one[: n - 1] + "…"


def _vec_stats(vec: list[float]) -> dict[str, Any]:
    if not vec:
        return {"dim": 0}
    norm = math.sqrt(sum(x * x for x in vec))
    return {
        "dim": len(vec),
        "l2_norm": round(norm, 6),
        "min": round(min(vec), 6),
        "max": round(max(vec), 6),
        "first_8": [round(x, 5) for x in vec[:8]],
    }


def show_index_overview(chroma_dir: Path) -> None:
    coll = _collection(chroma_dir)
    count = coll.count()
    print("=" * 72)
    print("CHROMA INDEX")
    print("=" * 72)
    print(f"  path:       {chroma_dir}")
    print(f"  collection: {coll.name}")
    print(f"  count:      {count}")
    print(f"  model:      {DEFAULT_MODEL}  (same at query time)")

    manifest = chroma_dir / "embed_manifest.json"
    if manifest.is_file():
        print(f"  manifest:   {manifest}")
        print(json.dumps(json.loads(manifest.read_text(encoding="utf-8")), indent=2))

    # Peek metadata distribution (no embeddings — faster)
    peek_n = min(count, 500)
    raw = coll.get(limit=peek_n, include=["metadatas"])
    metas = raw.get("metadatas") or []
    by_pub = Counter(str(m.get("publisher") or "?") for m in metas)
    by_sec = Counter(str(m.get("section_title") or "?") for m in metas)
    by_pri = Counter(int(m.get("priority") or 0) for m in metas)
    print("\n  by publisher:", dict(by_pub))
    print("  by priority: ", dict(sorted(by_pri.items())))
    print("  top sections:", by_sec.most_common(8))


def list_scheme_facts(chroma_dir: Path) -> None:
    coll = _collection(chroma_dir)
    raw = coll.get(include=["documents", "metadatas"])
    print("\n" + "=" * 72)
    print("GROWW SCHEME FACTS CHUNKS")
    print("=" * 72)
    for cid, doc, meta in zip(
        raw.get("ids") or [],
        raw.get("documents") or [],
        raw.get("metadatas") or [],
        strict=False,
    ):
        if str(meta.get("section_title") or "") != "Scheme Facts":
            continue
        print(f"\n[{cid}] pri={meta.get('priority')} scheme={meta.get('scheme_tag')}")
        print(f"  url: {meta.get('url')}")
        print(f"  text:\n{doc}\n")


def show_sample_vectors(chroma_dir: Path, n: int = 3) -> None:
    coll = _collection(chroma_dir)
    raw = coll.get(include=["embeddings", "documents", "metadatas"], limit=200)
    ids = list(raw.get("ids") or [])
    embs = raw.get("embeddings")
    docs = list(raw.get("documents") or [])
    metas = list(raw.get("metadatas") or [])
    if embs is None:
        print("No embeddings available from collection.get()")
        return

    chosen: list[tuple[str, Any, Any, Any]] = []
    for i, cid in enumerate(ids):
        meta = metas[i] if i < len(metas) else {}
        if str(meta.get("section_title") or "") == "Scheme Facts":
            chosen.append((cid, embs[i], docs[i] if i < len(docs) else "", meta))
        if len(chosen) >= n:
            break
    if len(chosen) < n:
        for i, cid in enumerate(ids):
            if any(c[0] == cid for c in chosen):
                continue
            meta = metas[i] if i < len(metas) else {}
            chosen.append((cid, embs[i], docs[i] if i < len(docs) else "", meta))
            if len(chosen) >= n:
                break

    print("\n" + "=" * 72)
    print(f"SAMPLE EMBEDDING VECTORS (n={len(chosen)})")
    print("=" * 72)
    for cid, emb, doc, meta in chosen:
        vec = [float(x) for x in list(emb)] if emb is not None else []
        stats = _vec_stats(vec)
        print(f"\n[{cid}]")
        print(f"  {meta.get('publisher')} | {meta.get('section_title')} | {meta.get('scheme_tag')}")
        print(f"  preview: {_preview(doc)}")
        print(f"  dim={stats.get('dim')} L2={stats.get('l2_norm')} first8={stats.get('first_8')}")


def show_embedding_vector(chroma_dir: Path, chunk_id: str) -> None:
    coll = _collection(chroma_dir)
    raw = coll.get(ids=[chunk_id], include=["embeddings", "documents", "metadatas"])
    ids = list(raw.get("ids") or [])
    if not ids:
        print(f"Chunk not found: {chunk_id}")
        return
    embs = raw.get("embeddings")
    docs = list(raw.get("documents") or [])
    metas = list(raw.get("metadatas") or [])
    emb = embs[0] if embs is not None and len(embs) else None
    doc = docs[0] if docs else ""
    meta = metas[0] if metas else {}
    print("\n" + "=" * 72)
    print(f"EMBEDDING VECTOR — {chunk_id}")
    print("=" * 72)
    print(f"  publisher={meta.get('publisher')} section={meta.get('section_title')}")
    print(f"  scheme={meta.get('scheme_tag')} priority={meta.get('priority')}")
    print(f"  preview: {_preview(doc, 200)}")
    if emb is None:
        print("  (no embedding returned)")
        return
    vec = [float(x) for x in list(emb)]
    stats = _vec_stats(vec)
    print(f"  dim:      {stats['dim']}")
    print(f"  L2 norm:  {stats['l2_norm']}  (≈1.0 if normalized)")
    print(f"  min/max:  {stats['min']} / {stats['max']}")
    print(f"  first 8:  {stats['first_8']}")


def run_retrieval_demo(
    query: str,
    *,
    top_k: int,
    use_pipeline_retrieve: bool,
    chroma_dir: Path,
) -> None:
    cfg = EmbedConfig(chroma_dir=chroma_dir)
    clf = classify(query)
    print("\n" + "=" * 72)
    print("EXAMPLE RETRIEVAL")
    print("=" * 72)
    print(f"  query:  {query}")
    print(f"  intent:  {clf.intent}")
    print(f"  scheme:  {clf.scheme_tag or '(none)'}")

    if clf.intent not in {"factual", "process_howto"}:
        print(
            f"\n  Note: intent={clf.intent!r} would skip Chroma in the live API "
            "(refusal path). Showing vector hits anyway for inspection.\n"
        )

    if use_pipeline_retrieve and clf.intent in {"factual", "process_howto"}:
        result = retrieve(query, scheme_tag=clf.scheme_tag, intent=clf.intent, top_k=top_k)
        hits = result.chunks
        print(f"  low_score: {result.low_score}  (threshold gate in retrieve.py)")
        print(f"  groww_url: {result.groww_url}")
    else:
        where = {"scheme_tag": clf.scheme_tag} if clf.scheme_tag else None
        hits = query_chunks(query, n_results=top_k, config=cfg, where=where)
        if clf.scheme_tag and not hits:
            hits = query_chunks(query, n_results=top_k, config=cfg, where=None)

    if not hits:
        print("  (no hits)")
        return

    print(f"\n  Top {len(hits)} chunks (priority-first re-rank + keyword boost):\n")
    for i, h in enumerate(hits, 1):
        meta = h.get("metadata") or {}
        print(
            f"  {i}. score={h.get('score', 0):.3f}  dist={h.get('distance', 0):.3f}  "
            f"pri={meta.get('priority')}  pub={meta.get('publisher')}  "
            f"scheme={meta.get('scheme_tag')}  section={meta.get('section_title')}"
        )
        print(f"     id={h.get('chunk_id')}")
        print(f"     url={meta.get('url')}")
        print(f"     {_preview(h.get('text') or '', 220)}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="View Chroma embeddings and example retrieval rankings"
    )
    parser.add_argument("--chroma-dir", type=Path, default=DEFAULT_CHROMA_DIR)
    parser.add_argument(
        "--query",
        "-q",
        action="append",
        default=[],
        help="Custom question (repeatable). Default: built-in FAQ examples",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--raw-chroma",
        action="store_true",
        help="Use query_chunks only (skip retrieve.py scheme/field promotions)",
    )
    parser.add_argument(
        "--show-vectors",
        action="store_true",
        help="Print sample embedding vectors (dim, norm, first values)",
    )
    parser.add_argument(
        "--chunk-id",
        default="",
        help="Show full embedding stats for one chunk_id",
    )
    parser.add_argument(
        "--list-facts",
        action="store_true",
        help="Print all Groww Scheme Facts chunk texts",
    )
    parser.add_argument(
        "--skip-retrieval",
        action="store_true",
        help="Only show index / vectors, do not run retrieval demos",
    )
    args = parser.parse_args(argv)

    chroma_dir = args.chroma_dir
    if not chroma_dir.is_dir():
        print(f"Missing Chroma dir: {chroma_dir}. Run: python scripts/build_index.py --skip-fetch")
        return 1

    try:
        show_index_overview(chroma_dir)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to open collection: {exc}")
        return 1

    if args.list_facts:
        list_scheme_facts(chroma_dir)

    if args.chunk_id:
        show_embedding_vector(chroma_dir, args.chunk_id)
    elif args.show_vectors:
        show_sample_vectors(chroma_dir, n=3)

    if not args.skip_retrieval:
        queries = args.query or EXAMPLE_QUERIES
        for q in queries:
            run_retrieval_demo(
                q,
                top_k=args.top_k,
                use_pipeline_retrieve=not args.raw_chroma,
                chroma_dir=chroma_dir,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
