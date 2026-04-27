# Medics4ALL Core Scribe (Tier 1) — self-contained image for local demos and pilots.
#
# Build (from this directory, which is the compose / build context root):
#   cd core_scribe_mvp
#   docker build -t medics4all-core-scribe .
#
# Run (UI + API on :8000):
#   docker run --rm -p 8000:8000 \
#     -e OPENAI_API_KEY=sk-... -e ASR_PROVIDER=openai -e LLM_PROVIDER=openai \
#     medics4all-core-scribe
#
# Or use `docker compose up` (see docker-compose.yml) for persisted data + optional Ollama.
#
# The API serves the static frontend; open http://127.0.0.1:8000 in a browser.
#
FROM python:3.12-slim-bookworm

# ffmpeg: decode WebM/MP3/FLAC; libgomp1: OpenMP for ctranslate2 (faster-whisper)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    KMP_DUPLICATE_LIB_OK=TRUE \
    OMP_NUM_THREADS=4

# Default HuggingFace cache (persists on the same /data volume as the DB; see docker-compose)
ENV HF_HOME=/data/huggingface

WORKDIR /app

# Install Python deps
COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/backend/requirements.txt

# Application: backend package (ROOT=/app) + static UI
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# Non-root: writable paths are only under /data (see MEDICS4ALL_DATA in config)
RUN useradd --create-home --uid 1000 scribe \
    && mkdir -p /data/storage/audio /data/huggingface \
    && chown -R scribe:scribe /app /data

USER scribe
WORKDIR /app/backend

# Persist SQLite + audio + model downloads on a single named volume
ENV MEDICS4ALL_DATA=/data

EXPOSE 8000

# No --reload in production; adjust start timeout for first-run model fetch
HEALTHCHECK --interval=30s --timeout=8s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=5).read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
