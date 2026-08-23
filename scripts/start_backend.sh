#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
mkdir -p "$RUN_DIR"
cd "$ROOT_DIR"

VOICE_AGENT_PORT=8003 bash scripts/start_voice_agent.sh

if [[ -z "${MODEL_CATALOG_PROXY:-}" ]]; then
  WSL_GATEWAY="$(ip route show default 2>/dev/null | awk '{print $3; exit}')"
  for port in 7897 7890; do
    if [[ -n "$WSL_GATEWAY" ]] && timeout 1 bash -c ">/dev/tcp/$WSL_GATEWAY/$port" 2>/dev/null; then
      export MODEL_CATALOG_PROXY="http://$WSL_GATEWAY:$port"
      echo "Model catalog will use local proxy: $MODEL_CATALOG_PROXY"
      break
    fi
  done
fi

if [[ -f "$RUN_DIR/backend.pid" ]] && kill -0 "$(cat "$RUN_DIR/backend.pid")" 2>/dev/null; then
  echo "FastAPI backend is already running (PID $(cat "$RUN_DIR/backend.pid"))."
else
  rm -f "$RUN_DIR/backend.pid"
  if ss -H -ltn "sport = :8002" 2>/dev/null | grep -q .; then
    echo "Cannot start FastAPI backend: port 8002 is used by an unmanaged process." >&2
    exit 1
  fi
  nohup setsid "$ROOT_DIR/.venv-wsl/bin/uvicorn" backend.main:app \
    --host 127.0.0.1 --port 8002 >"$ROOT_DIR/backend.log" 2>&1 &
  echo $! >"$RUN_DIR/backend.pid"
  echo "Started FastAPI backend (PID $!)."
fi

for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8002/api/health 2>/dev/null | grep -q '"ready":true'; then
    echo "FastAPI backend is ready: http://127.0.0.1:8002"
    exit 0
  fi
  sleep 1
done

echo "FastAPI backend did not become ready. See $ROOT_DIR/backend.log" >&2
exit 1
