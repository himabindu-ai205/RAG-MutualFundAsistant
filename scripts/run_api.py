"""Run FastAPI serve: uvicorn src.serve.api:app"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8000


def _resolve_port(raw: str | None, *, default: int = DEFAULT_PORT) -> int:
    """Parse PORT safely; fall back to default on missing/invalid values."""
    if raw is None or not str(raw).strip():
        return default
    try:
        port = int(str(raw).strip())
    except ValueError:
        logger.warning("Invalid PORT=%r; using default %s", raw, default)
        return default
    if not (1 <= port <= 65535):
        logger.warning("PORT %s out of range 1–65535; using default %s", port, default)
        return default
    return port


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    host = (os.getenv("HOST") or "127.0.0.1").strip() or "127.0.0.1"
    port = _resolve_port(os.getenv("PORT"))
    uvicorn.run("src.serve.api:app", host=host, port=port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
