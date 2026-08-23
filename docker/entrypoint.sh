#!/usr/bin/env bash
set -euo pipefail

ASR_MODEL_PATH="${ASR_MODEL_PATH:-/models/Qwen3-ASR-0.6B}"
TTS_MODEL_PATH="${TTS_MODEL_PATH:-/models/Qwen3-TTS-12Hz-0.6B-CustomVoice}"
APP_PORT="${APP_PORT:-8000}"

for model_path in "$ASR_MODEL_PATH" "$TTS_MODEL_PATH"; do
  if [[ ! -f "$model_path/config.json" ]]; then
    echo "Required model is missing: $model_path" >&2
    echo "Mount the project models directory at /models." >&2
    exit 2
  fi
done

pids=()
cleanup() {
  trap - EXIT INT TERM
  if ((${#pids[@]})); then kill "${pids[@]}" 2>/dev/null || true; fi
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait_for() {
  local name="$1" url="$2" timeout="$3"
  for _ in $(seq 1 "$timeout"); do
    if curl -fsS "$url" >/dev/null 2>&1; then echo "$name is ready."; return 0; fi
    sleep 1
  done
  echo "$name did not become ready within ${timeout}s." >&2
  return 1
}

echo "Starting Qwen3-ASR on the internal model-worker port..."
/opt/venvs/asr/bin/qwen-asr-demo-streaming \
  --asr-model-path "$ASR_MODEL_PATH" \
  --gpu-memory-utilization "${ASR_GPU_MEMORY_UTILIZATION:-0.45}" \
  --max-model-len "${ASR_MAX_MODEL_LEN:-16384}" \
  --host 127.0.0.1 --port 8003 &
pids+=("$!")
wait_for "Qwen3-ASR" http://127.0.0.1:8003/api/voice/health "${MODEL_START_TIMEOUT:-300}"

echo "Starting Qwen3-TTS on the internal model-worker port..."
/opt/venvs/tts/bin/python /app/qwen3-tts-service/app.py \
  --model-path "$TTS_MODEL_PATH" --host 127.0.0.1 --port 8001 &
pids+=("$!")
wait_for "Qwen3-TTS" http://127.0.0.1:8001/health "${MODEL_START_TIMEOUT:-300}"

uvicorn_args=(backend.main:app --host 0.0.0.0 --port "$APP_PORT" --proxy-headers)
if [[ -n "${TLS_CERT_FILE:-}" || -n "${TLS_KEY_FILE:-}" ]]; then
  if [[ ! -f "${TLS_CERT_FILE:-}" || ! -f "${TLS_KEY_FILE:-}" ]]; then
    echo "TLS_CERT_FILE and TLS_KEY_FILE must both point to mounted certificate files." >&2
    exit 2
  fi
  uvicorn_args+=(--ssl-certfile "$TLS_CERT_FILE" --ssl-keyfile "$TLS_KEY_FILE")
fi

echo "Starting Qwen Voice Workspace on port $APP_PORT..."
/opt/venvs/asr/bin/uvicorn "${uvicorn_args[@]}" &
pids+=("$!")
set +e
wait -n "${pids[@]}"
exit_code=$?
set -e
echo "A managed service exited with status $exit_code; stopping the container." >&2
exit "$exit_code"
