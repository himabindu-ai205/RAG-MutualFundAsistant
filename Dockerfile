# syntax=docker/dockerfile:1

# --- React UI ---
FROM node:22-alpine AS ui
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

# --- FastAPI + Chroma ---
FROM python:3.11-slim AS app
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY scripts ./scripts
COPY docs ./docs
COPY data ./data
COPY disclaimer.txt .
COPY --from=ui /ui/dist ./ui/dist

# Warm the embedding model, then (re)build Chroma from committed chunks.jsonl
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('jinaai/jina-embeddings-v2-base-en', trust_remote_code=True)" \
    && python scripts/embed_corpus.py

EXPOSE 8000

# Use run_api.py so PORT is validated (invalid values fall back to 8000).
ENV HOST=0.0.0.0
CMD ["python", "scripts/run_api.py"]
