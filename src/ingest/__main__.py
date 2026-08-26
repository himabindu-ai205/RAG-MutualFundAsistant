"""Allow `python -m src.ingest` as an alias for scripts/build_index.py."""

from src.ingest.build_index import main

if __name__ == "__main__":
    raise SystemExit(main())
