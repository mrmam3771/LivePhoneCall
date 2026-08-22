#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"

stop_service() {
  local name="$1" pid_file="$2"
  if [[ ! -f "$pid_file" ]]; then echo "$name is not running."; return; fi
  local pid
  pid="$(cat "$pid_file")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    for _ in $(seq 1 30); do
      if ! kill -0 "$pid" 2>/dev/null; then
        echo "Stopped $name (PID $pid)."
        rm -f "$pid_file"
        return
      fi
      sleep 1
    done
    echo "$name did not stop within 30s (PID $pid)." >&2
    return 1
  fi
  rm -f "$pid_file"
}

stop_service "Qwen3-ASR voice agent" "$RUN_DIR/asr.pid"
stop_service "Qwen3-TTS" "$RUN_DIR/tts.pid"
