"""Phase 2.4 — Embed chunks into Chroma with local sentence-transformers.

Same embedding model must be used at query time. Optional hybrid hint:
keyword tokens (exit load, SIP, lock-in, TER, scheme names) are stored in
metadata for later re-ranking.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from src.ingest.chunk import Chunk, chunk_all
from src.ingest.registry import ROOT

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CHROMA_DIR = ROOT / "data" / "chroma"
DEFAULT_CHUNKS_JSONL = ROOT / "data" / "chunks.jsonl"
COLLECTION_NAME = "mf_faq_chunks"

# Reuse embedder + Chroma client across online queries (avoid ~10s cold load per request).
_EMBEDDER_CACHE: dict[str, object] = {}
_CHROMA_QUERY_CACHE: dict[str, object] = {}

KEYWORD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("nav", re.compile(r"\bNAV\b|net\s+asset\s+value", re.I)),
    ("exit_load", re.compile(r"\bexit\s*load\b", re.I)),
    ("sip", re.compile(r"\bSIP\b|\bmin(?:imum)?\s+(?:for\s+)?SIP\b", re.I)),
    ("lock_in", re.compile(r"\block[\s-]*in\b", re.I)),
    ("ter", re.compile(r"\bTER\b|\bexpense\s*ratio\b", re.I)),
    ("riskometer", re.compile(r"\brisk[\s-]*o?meter\b|\bvery high risk\b", re.I)),
    ("benchmark", re.compile(r"\bbenchmark\b", re.I)),
    ("large_cap", re.compile(r"\blarge\s*cap\b|\bbluechip\b", re.I)),
    ("flexicap", re.compile(r"\bflexi\s*cap\b|\bflexicap\b", re.I)),
    ("elss", re.compile(r"\bELSS\b|\btax\s*saver\b", re.I)),
    ("contra", re.compile(r"\bcontra\b", re.I)),
    ("small_cap", re.compile(r"\bsmall\s*cap\b|\bsmall[\s-]*midcap\b", re.I)),
]


@dataclass(frozen=True)
class EmbedConfig:
    model_name: str = DEFAULT_MODEL
    chroma_dir: Path = DEFAULT_CHROMA_DIR
    collection_name: str = COLLECTION_NAME
    batch_size: int = 64


def extract_keywords(text: str, scheme: str = "") -> str:
    """Comma-separated keyword tags for hybrid retrieval boost."""
    tags: list[str] = []
    for name, pattern in KEYWORD_PATTERNS:
        if pattern.search(text):
            tags.append(name)
    if scheme:
        tags.append(re.sub(r"\s+", "_", scheme.strip().lower())[:64])
    # Stable unique order
    seen: set[str] = set()
    ordered: list[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ",".join(ordered)


def load_chunks_jsonl(path: Path = DEFAULT_CHUNKS_JSONL) -> list[Chunk]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing chunks file: {path}. Run scripts/chunk_corpus.py first.")
    chunks: list[Chunk] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            chunks.append(
                Chunk(
                    chunk_id=raw["chunk_id"],
                    text=raw["text"],
                    source_id=raw["source_id"],
                    url=raw["url"],
                    scheme=raw["scheme"],
                    scheme_tag=raw["scheme_tag"],
                    doc_type=raw["doc_type"],
                    publisher=raw["publisher"],
                    section_title=raw["section_title"],
                    retrieved_on=raw.get("retrieved_on") or "",
                    priority=int(raw["priority"]),
                    local_path=raw["local_path"],
                )
            )
    return chunks


def _get_embedder(model_name: str):
    from sentence_transformers import SentenceTransformer

    if model_name not in _EMBEDDER_CACHE:
        logger.info("Loading embedding model %s", model_name)
        _EMBEDDER_CACHE[model_name] = SentenceTransformer(model_name)
    return _EMBEDDER_CACHE[model_name]


def _get_query_client(chroma_dir: Path):
    """Reuse Chroma client + collection across requests (same path)."""
    key = str(chroma_dir.resolve())
    if key not in _CHROMA_QUERY_CACHE:
        import chromadb
        from chromadb.config import Settings

        client = chromadb.PersistentClient(
            path=key,
            settings=Settings(anonymized_telemetry=False),
        )
        _CHROMA_QUERY_CACHE[key] = client
    return _CHROMA_QUERY_CACHE[key]


def _get_collection(
    chroma_dir: Path,
    collection_name: str,
    *,
    model_name: str,
    reset: bool = True,
):
    import chromadb
    from chromadb.config import Settings

    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=Settings(anonymized_telemetry=False),
    )
    if reset:
        try:
            client.delete_collection(collection_name)
            logger.info("Deleted existing collection %s", collection_name)
        except Exception:  # noqa: BLE001
            pass
    return client, client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine", "embedding_model": model_name},
    )


def embed_chunks(
    chunks: Sequence[Chunk],
    *,
    config: EmbedConfig | None = None,
    reset: bool = True,
) -> dict[str, Any]:
    """Embed chunks and persist to Chroma. Returns a summary dict."""
    cfg = config or EmbedConfig()
    if not chunks:
        raise ValueError("No chunks to embed")

    # Groww / priority first for deterministic id ordering (already expected from chunker)
    ordered = sorted(
        chunks,
        key=lambda c: (c.priority, 0 if c.publisher.upper() == "GROWW" else 1, c.chunk_id),
    )

    model = _get_embedder(cfg.model_name)
    client, collection = _get_collection(
        cfg.chroma_dir, cfg.collection_name, model_name=cfg.model_name, reset=reset
    )

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str | int]] = []

    for ch in ordered:
        # Prefix section + keywords lightly so vectors lean toward FAQ terms (hybrid hint).
        keywords = extract_keywords(ch.text, ch.scheme)
        enrich = f"[{ch.section_title}] [{ch.scheme}]"
        if keywords:
            enrich += f" keywords:{keywords}"
        doc_text = f"{enrich}\n{ch.text}".strip()
        meta = ch.metadata()
        meta["keywords"] = keywords
        meta["embedding_model"] = cfg.model_name
        ids.append(ch.chunk_id)
        documents.append(doc_text)
        metadatas.append(meta)

    total = len(ids)
    logger.info("Embedding %d chunks with %s", total, cfg.model_name)
    for start in range(0, total, cfg.batch_size):
        end = min(total, start + cfg.batch_size)
        batch_docs = documents[start:end]
        vectors = model.encode(
            batch_docs,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        collection.add(
            ids=ids[start:end],
            documents=batch_docs,
            metadatas=metadatas[start:end],
            embeddings=vectors.tolist(),
        )
        logger.info("Upserted %d / %d", end, total)

    by_pub: dict[str, int] = {}
    groww = 0
    for ch in ordered:
        by_pub[ch.publisher] = by_pub.get(ch.publisher, 0) + 1
        if ch.publisher.upper() == "GROWW":
            groww += 1

    summary = {
        "collection": cfg.collection_name,
        "chroma_dir": str(cfg.chroma_dir),
        "model": cfg.model_name,
        "count": total,
        "groww_chunks": groww,
        "by_publisher": by_pub,
    }
    # Persist a small manifest for query-time model alignment
    manifest = cfg.chroma_dir / "embed_manifest.json"
    manifest.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Wrote %s", manifest)
    return summary


def query_chunks(
    query: str,
    *,
    n_results: int = 6,
    config: EmbedConfig | None = None,
    where: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Query Chroma and lightly re-rank by priority + keyword overlap (hybrid)."""
    cfg = config or EmbedConfig()
    client = _get_query_client(cfg.chroma_dir)
    collection = client.get_collection(cfg.collection_name)
    model = _get_embedder(cfg.model_name)
    q_vec = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]

    raw = collection.query(
        query_embeddings=[q_vec.tolist()],
        n_results=max(n_results * 3, n_results),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    ids = (raw.get("ids") or [[]])[0]
    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]

    q_keywords = set(extract_keywords(query).split(",")) - {""}
    scored: list[tuple[float, dict[str, Any]]] = []
    for i, chunk_id in enumerate(ids):
        meta = metas[i] or {}
        dist = float(dists[i]) if dists else 1.0
        # cosine distance: lower is better → convert to similarity
        sim = 1.0 - dist
        priority = int(meta.get("priority") or 3)
        # Prefer Groww / priority=1 (Architecture: re-rank by priority then similarity)
        priority_boost = {1: 0.15, 2: 0.03, 3: 0.0}.get(priority, 0.0)
        kw = set(str(meta.get("keywords") or "").split(",")) - {""}
        kw_boost = 0.04 * len(q_keywords & kw)
        score = sim + priority_boost + kw_boost
        scored.append(
            (
                score,
                priority,
                {
                    "chunk_id": chunk_id,
                    "text": docs[i],
                    "metadata": meta,
                    "distance": dist,
                    "score": score,
                },
            )
        )

    # Architecture: re-rank by priority then similarity (Groww priority=1 first)
    scored.sort(key=lambda x: (x[1], -x[0]))
    return [item for _, _, item in scored[:n_results]]


def warmup_query_engine(config: EmbedConfig | None = None) -> None:
    """Preload embedder + Chroma on API startup to avoid first-request cold start."""
    cfg = config or EmbedConfig()
    try:
        _get_embedder(cfg.model_name)
        query_chunks("ELSS lock-in", n_results=1, config=cfg)
        logger.info("Query engine warmed up (model=%s chroma=%s)", cfg.model_name, cfg.chroma_dir)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Query engine warmup skipped: %s", exc)


def build_index_from_chunks_file(
    chunks_path: Path = DEFAULT_CHUNKS_JSONL,
    *,
    config: EmbedConfig | None = None,
    reset: bool = True,
) -> dict[str, Any]:
    chunks = load_chunks_jsonl(chunks_path)
    return embed_chunks(chunks, config=config, reset=reset)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 2.4 embed chunks into Chroma")
    parser.add_argument(
        "--chunks",
        type=Path,
        default=DEFAULT_CHUNKS_JSONL,
        help="Path to chunks.jsonl",
    )
    parser.add_argument(
        "--rebuild-chunks",
        action="store_true",
        help="Re-parse/chunk from sources before embedding",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--chroma-dir", type=Path, default=DEFAULT_CHROMA_DIR)
    parser.add_argument("--no-reset", action="store_true", help="Do not delete existing collection")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="After embed, run ELSS lock-in / Flexicap exit-load smoke queries",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    cfg = EmbedConfig(model_name=args.model, chroma_dir=args.chroma_dir)

    if args.rebuild_chunks:
        logger.info("Rebuilding chunks from sources…")
        from dataclasses import asdict as dc_asdict

        docs_chunks = chunk_all(skip_missing=True)
        args.chunks.parent.mkdir(parents=True, exist_ok=True)
        with args.chunks.open("w", encoding="utf-8") as f:
            for ch in docs_chunks:
                f.write(json.dumps(dc_asdict(ch), ensure_ascii=False) + "\n")
        logger.info("Wrote %s (%d chunks)", args.chunks, len(docs_chunks))

    try:
        summary = build_index_from_chunks_file(
            args.chunks, config=cfg, reset=not args.no_reset
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("%s", exc)
        return 1

    print(
        f"Embedded {summary['count']} chunks "
        f"(Groww={summary['groww_chunks']}) -> {summary['chroma_dir']} "
        f"[{summary['collection']}] model={summary['model']}"
    )
    print(f"by publisher: {summary['by_publisher']}")

    if args.smoke:
        for q in ("ELSS lock-in", "exit load Flexicap"):
            hits = query_chunks(q, n_results=5, config=cfg)
            print(f"\nSMOKE: {q!r}")
            for h in hits:
                meta = h["metadata"]
                print(
                    f"  pri={meta.get('priority')} pub={meta.get('publisher')} "
                    f"scheme={meta.get('scheme_tag')} section={meta.get('section_title')} "
                    f"score={h['score']:.3f} id={h['chunk_id']}"
                )
            if hits and int(hits[0]["metadata"].get("priority") or 99) != 1:
                logger.warning("Top hit is not priority=1 (Groww) for %r", q)
    return 0


if __name__ == "__main__":
    sys.exit(main())
