# Mutual Fund FAQ Assistant (Facts-Only RAG)

Lightweight RAG FAQ assistant for **SBI Mutual Fund** schemes in a **Groww** product context.

**Primary source:** Groww scheme pages (`groww.in/mutual-funds/...`).  
**Supporting corpus:** SBI KIM/SID PDFs and official SBI / AMFI / SEBI pages.

> **Facts-only. No investment advice.**

## Docs

| Doc | Purpose |
| --- | --- |
| [docs/problemStatement.md](docs/problemStatement.md) | Project brief and deliverables |
| [docs/Architecture.md](docs/Architecture.md) | System design (Groww-primary dual ingest) |
| [docs/implementation-plan.md](docs/implementation-plan.md) | Phase-wise build plan |
| [docs/stitch-prompt-phase4.md](docs/stitch-prompt-phase4.md) | Google Stitch prompt (Phase 4 UI) |
| [docs/edge-case.md](docs/edge-case.md) | Edge cases |
| [docs/eval.md](docs/eval.md) | Evaluation protocol |

## Scope (preview)

- **AMC:** SBI Mutual Fund  
- **Schemes (5):** Large Cap, Flexicap, ELSS Tax Saver, Contra, Small Midcap / Small Cap (see Architecture naming note)  
- **Stack:** Python 3.11+, Groq, sentence-transformers, Chroma, FastAPI, React (Vite) from Google Stitch  

## Setup (Phase 0)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # then set GROQ_API_KEY
```

Full ingest / run steps will be documented in **Phase 5**. Rebuild the Chroma index with:

```bash
python scripts/build_index.py          # Groww fetch (required) → PDFs → shared → parse → chunk → embed
python scripts/build_index.py --skip-fetch --smoke   # reuse docs/corpus snapshots
# alias: python -m src.ingest
```

Run the chat API and UI (Phase 3–4):

```bash
# ensure GROQ_API_KEY and GROQ_MODEL=openai/gpt-oss-120b in .env
# min tokens: GROQ_REASONING_EFFORT=low GROQ_MAX_TOKENS=256 GROQ_CONTEXT_CHUNKS=3 GROQ_CONTEXT_CHARS=480
cd ui
npm install
npm run build
cd ..
python scripts/run_api.py
# UI:  http://127.0.0.1:8000/
# POST http://127.0.0.1:8000/chat  {"question":"Exit load of SBI Flexicap?"}
python scripts/smoke_chat.py
```

During UI work, keep the API running and use the Vite dev server (proxies `/chat`):

```bash
python scripts/run_api.py
cd ui && npm run dev
# http://127.0.0.1:5173/
```

The Google Stitch export lives in `stitch_sbi_mutual_fund_faq_assistant/`. The React app in `ui/` is the implementation (not Streamlit).

## Status

- [x] Phase 0 — Bootstrap  
- [x] Phase 1 — Source registry (`docs/sources.md`)  
- [x] Phase 2 — Dual ingest → Chroma  
- [x] Phase 3 — Chat API  
- [x] Phase 4 — Google Stitch UI (React in `ui/`)  
- [ ] Phase 5 — Eval + submission pack  
- [x] Phase 6 — Daily ingest scheduler (GitHub Actions, 17:30 SGT)

## Daily corpus refresh (GitHub Actions)

The retrieval index is refreshed **every day at 17:30 Singapore Time (SGT)** by GitHub Actions (cron `30 9 * * *` UTC). The job re-runs the full Phase 2 pipeline:

`scrape (Groww → PDFs → shared) → parse → chunk → embed → update Chroma`

Workflow: [`.github/workflows/daily-ingest.yml`](.github/workflows/daily-ingest.yml)

| Item | Detail |
| --- | --- |
| Schedule | **17:30 SGT daily** (09:30 UTC) |
| Manual run | GitHub → **Actions** → **Daily ingest** → **Run workflow** |
| Entrypoint | `python scripts/build_index.py` (never `--skip-fetch` on the daily job) |
| Artifact | `chroma-index-<run_id>` = full `data/chroma/` (14-day retention) |
| Bot commit | Groww/shared HTML, `data/chunks.jsonl`, `embed_manifest.json`, source stamps when changed |

`POST /chat` does **not** browse the live web. It answers from the last built Chroma index. After a successful daily run, refresh a local/deployed API like this:

```bash
# requires GitHub CLI: https://cli.github.com/  (gh auth login)
python scripts/pull_latest_chroma.py
python scripts/run_api.py
```

Or download a specific run:

```bash
python scripts/pull_latest_chroma.py --run-id <GITHUB_RUN_ID>
```

Scheduled workflows only run on the **default branch** (`main`). Use **Run workflow** to test from another branch after merging the YAML to `main`.

## Deploy on Railway

Railway’s default Python builder looks for `main.py` / `app.py`. This app lives at `src/serve/api.py`, so the repo includes a **Dockerfile** + [`railway.toml`](railway.toml).

1. Connect the GitHub repo and deploy from `main`.
2. In the service **Variables**, set at least:
   - `GROQ_API_KEY` — required for generated answers  
   - `GROQ_MODEL=openai/gpt-oss-120b` (optional; this is the code default)
3. Generate a public domain (**Settings → Networking → Generate domain**).
4. Confirm `GET /health` returns `{"status":"ok"}`.

The image builds the React UI and rebuilds Chroma from `data/chunks.jsonl` at **build** time. Daily ingest commits that update `chunks.jsonl` will trigger a new Railway deploy and a fresh index. Do **not** commit `.env`.
