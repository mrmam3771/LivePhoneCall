#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
mkdir -p "$RUN_DIR"
cd "$ROOT_DIR"

port_is_listening() {
  ss -H -ltn "sport = :$1" 2>/dev/null | grep -q .
}

start_if_stopped() {
  local name="$1" pid_file="$2" log_file="$3" port="$4"
  shift 4
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "$name is already running (PID $(cat "$pid_file"))."
    return
  fi
  rm -f "$pid_file"
  if port_is_listening "$port"; then
    echo "Cannot start $name: port $port is already in use by an unmanaged process." >&2
    exit 1
  fi
  nohup "$@" >"$log_file" 2>&1 &
  echo $! >"$pid_file"
  echo "Started $name (PID $!)."
}

wait_until_ready() {
  local name="$1" pid_file="$2" url="$3" pattern="$4" log_file="$5" timeout="$6"
  local pid
  pid="$(cat "$pid_file")"
  for _ in $(seq 1 "$timeout"); do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "$name exited before becoming ready. See $log_file" >&2
      tail -n 40 "$log_file" >&2 || true
      rm -f "$pid_file"
      exit 1
    fi
    if curl -fsS "$url" 2>/dev/null | grep -q "$pattern"; then
      echo "$name is ready."
      return
    fi
    sleep 1
  done
  echo "$name did not become ready within ${timeout}s. See $log_file" >&2
  exit 1
}

if [[ ! -x qwen3-tts-service/.venv/bin/python ]]; then
  echo "TTS environment is missing. Run: cd qwen3-tts-service && uv sync"
  exit 1
fi
if [[ ! -d models/Qwen3-TTS-12Hz-0.6B-CustomVoice ]]; then
  echo "TTS weights are missing. Run: uv run --project qwen3-tts-service qwen3-tts-service/download_model.py"
  exit 1
fi

start_if_stopped "Qwen3-TTS" "$RUN_DIR/tts.pid" "$ROOT_DIR/qwen3-tts-service.log" 8001 \
  "$ROOT_DIR/qwen3-tts-service/.venv/bin/python" "$ROOT_DIR/qwen3-tts-service/app.py" \
  --model-path "$ROOT_DIR/models/Qwen3-TTS-12Hz-0.6B-CustomVoice" --host 127.0.0.1 --port 8001

echo "Waiting for Qwen3-TTS model..."
wait_until_ready "Qwen3-TTS" "$RUN_DIR/tts.pid" http://127.0.0.1:8001/health \
  '"ready":true' "$ROOT_DIR/qwen3-tts-service.log" 240

start_if_stopped "Qwen3-ASR voice agent" "$RUN_DIR/asr.pid" "$ROOT_DIR/qwen3-asr-service.log" 8000 \
  env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TTS_SERVICE_URL=http://127.0.0.1:8001 \
  "$ROOT_DIR/.venv-wsl/bin/qwen-asr-demo-streaming" \
  --asr-model-path "$ROOT_DIR/models/Qwen3-ASR-0.6B" --gpu-memory-utilization 0.45 \
  --max-model-len 16384 --host 0.0.0.0 --port 8000

echo "Waiting for Qwen3-ASR voice agent..."
wait_until_ready "Qwen3-ASR voice agent" "$RUN_DIR/asr.pid" http://127.0.0.1:8000/api/voice/health \
  '"agent"' "$ROOT_DIR/qwen3-asr-service.log" 240

echo "Voice agent: http://127.0.0.1:8000"
