"""Run FastAPI serve: uvicorn src.serve.api:app"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn


def main() -> int:
    uvicorn.run("src.serve.api:app", host="127.0.0.1", port=8000, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
