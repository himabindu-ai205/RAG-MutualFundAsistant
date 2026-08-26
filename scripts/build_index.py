"""Single offline entrypoint: Groww → PDFs → shared → parse → chunk → embed."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest.build_index import main

if __name__ == "__main__":
    raise SystemExit(main())
