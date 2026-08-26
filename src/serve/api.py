"""Phase 3.6 — FastAPI POST /chat. Phase 4 — serve React UI from ui/dist."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.ingest.registry import ROOT
from src.serve.pipeline import answer_question

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

UI_DIST = ROOT / "ui" / "dist"

app = FastAPI(
    title="Mutual Fund FAQ Assistant",
    description="Facts-only RAG FAQ for SBI schemes (Groww-primary citations).",
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: Request) -> Any:
    """Accept only {\"question\": \"...\"}. Empty/missing → 400 question_required."""
    try:
        raw = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse(status_code=400, content={"error": "question_required"})

    if not isinstance(raw, dict):
        return JSONResponse(status_code=400, content={"error": "question_required"})

    question = str(raw.get("question") or "").strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "question_required"})

    extra = set(raw.keys()) - {"question"}
    if extra:
        logger.info("Ignoring extra fields: %s", sorted(extra))

    result = answer_question(question)
    if result.get("error") == "question_required":
        return JSONResponse(status_code=400, content={"error": "question_required"})

    return {
        "intent": result["intent"],
        "answer": result["answer"],
        "source": result["source"],
        "last_updated_from_sources": result["last_updated_from_sources"],
        "disclaimer": result["disclaimer"],
        "request_id": result.get("request_id"),
    }


if UI_DIST.is_dir() and (UI_DIST / "index.html").is_file():
    app.mount("/", StaticFiles(directory=str(UI_DIST), html=True), name="ui")
    logger.info("Serving React UI from %s", UI_DIST)
else:

    @app.get("/")
    def ui_not_built() -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "error": "ui_not_built",
                "hint": "cd ui && npm install && npm run build",
            },
        )

    logger.warning("UI build missing at %s — run: cd ui && npm run build", UI_DIST)


def create_app() -> FastAPI:
    return app
