# syntax=docker/dockerfile:1.7
FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile
COPY frontend/ ./
RUN yarn build

FROM python:3.12-slim-bookworm AS runtime
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    UV_LINK_MODE=copy \
    MODEL_WORKER_URL=http://127.0.0.1:8003 \
    TTS_SERVICE_URL=http://127.0.0.1:8001 \
    CHAT_DATABASE_PATH=/data/chat-data.sqlite3 \
    FRONTEND_DIST=/app/frontend/dist

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl libsndfile1 sox ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.11.7

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY Qwen3-ASR/ ./Qwen3-ASR/
RUN UV_PROJECT_ENVIRONMENT=/opt/venvs/asr uv sync --locked --no-dev --no-install-project

COPY qwen3-tts-service/pyproject.toml qwen3-tts-service/uv.lock ./qwen3-tts-service/
RUN UV_PROJECT_ENVIRONMENT=/opt/venvs/tts uv sync --project qwen3-tts-service --locked --no-dev

COPY backend/ ./backend/
COPY chat_store.py main.py ./
COPY qwen3-tts-service/ ./qwen3-tts-service/
COPY docker/entrypoint.sh /usr/local/bin/qwen-voice-entrypoint
COPY --from=frontend-build /build/frontend/dist ./frontend/dist/

RUN chmod +x /usr/local/bin/qwen-voice-entrypoint \
    && mkdir -p /data /models \
    && useradd --create-home --uid 10001 app \
    && chown -R app:app /app /data

USER app
EXPOSE 8000
VOLUME ["/data", "/models"]
HEALTHCHECK --interval=20s --timeout=5s --start-period=300s --retries=5 CMD if [ -n "$TLS_CERT_FILE" ]; then curl -fkSs https://127.0.0.1:8000/api/health; else curl -fSs http://127.0.0.1:8000/api/health; fi
ENTRYPOINT ["qwen-voice-entrypoint"]
