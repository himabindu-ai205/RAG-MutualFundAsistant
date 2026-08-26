"""Download the latest successful Daily ingest Chroma artifact into data/chroma/.

Requires GitHub CLI (`gh`) authenticated to this repo.

Usage:
  python scripts/pull_latest_chroma.py
  python scripts/pull_latest_chroma.py --run-id 123456789
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHROMA_DIR = ROOT / "data" / "chroma"
WORKFLOW = "daily-ingest.yml"


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=True, cwd=ROOT)


def _latest_run_id() -> str:
    # Prefer successful completed runs of the daily-ingest workflow
    result = _run(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            WORKFLOW,
            "--status",
            "success",
            "--limit",
            "1",
            "--json",
            "databaseId",
            "--jq",
            ".[0].databaseId",
        ]
    )
    run_id = (result.stdout or "").strip()
    if not run_id or run_id == "null":
        raise SystemExit(
            f"No successful runs found for workflow {WORKFLOW}. "
            "Trigger Actions → Daily ingest → Run workflow first."
        )
    return run_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pull latest Chroma artifact from Daily ingest")
    parser.add_argument("--run-id", help="GitHub Actions run id (default: latest success)")
    parser.add_argument(
        "--out",
        type=Path,
        default=CHROMA_DIR,
        help="Destination Chroma directory (default: data/chroma)",
    )
    args = parser.parse_args(argv)

    if shutil.which("gh") is None:
        print("GitHub CLI `gh` not found. Install: https://cli.github.com/", file=sys.stderr)
        return 1

    run_id = args.run_id or _latest_run_id()
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="chroma-artifact-") as tmp:
        tmp_path = Path(tmp)
        print(f"Downloading chroma artifact from run {run_id}…")
        # Artifact name is chroma-index-<run_id>; pattern match is fine
        dl = _run(
            [
                "gh",
                "run",
                "download",
                run_id,
                "-n",
                f"chroma-index-{run_id}",
                "-D",
                str(tmp_path),
            ],
            check=False,
        )
        if dl.returncode != 0:
            # Fallback: download all artifacts from the run
            print(dl.stderr or dl.stdout, file=sys.stderr)
            _run(["gh", "run", "download", run_id, "-D", str(tmp_path)])

        # Locate chroma payload (upload-artifact keeps data/chroma/ layout)
        src_root: Path | None = None
        for candidate in (
            tmp_path / "data" / "chroma",
            tmp_path / "chroma",
        ):
            if candidate.is_dir() and (
                (candidate / "embed_manifest.json").is_file()
                or any(candidate.glob("**/chroma.sqlite3"))
            ):
                src_root = candidate
                break
        if src_root is None:
            hits = list(tmp_path.rglob("embed_manifest.json")) + list(
                tmp_path.rglob("chroma.sqlite3")
            )
            if hits:
                src_root = hits[0].parent
        if src_root is None:
            print("Could not find Chroma files in the artifact.", file=sys.stderr)
            return 1

        # Replace destination contents (keep .gitkeep)
        for child in out.iterdir():
            if child.name == ".gitkeep":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

        for child in src_root.iterdir():
            dest = out / child.name
            if child.is_dir():
                shutil.copytree(child, dest)
            else:
                shutil.copy2(child, dest)

    print(f"Updated {out}")
    manifest = out / "embed_manifest.json"
    if manifest.is_file():
        print(manifest.read_text(encoding="utf-8")[:500])
    print("Restart the API (`python scripts/run_api.py`) to load the new index.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
