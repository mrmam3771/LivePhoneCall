"""Internal HTTP service for Qwen3-TTS CustomVoice inference."""

from __future__ import annotations

import argparse
import importlib.util
import io
import threading
from pathlib import Path

import soundfile as sf
import torch
from flask import Flask, Response, jsonify, request
from qwen_tts import Qwen3TTSModel


class QwenTTSService:
    def __init__(self, model_path: str, device: str = "cuda:0"):
        self.model_path = model_path
        self.device = device
        self.model = None
        self.sample_rate = None
        self._lock = threading.Lock()

    def load(self) -> None:
        if self.model is not None:
            return
        attention = "flash_attention_2" if importlib.util.find_spec("flash_attn") else "sdpa"
        dtype = torch.bfloat16 if self.device.startswith("cuda") else torch.float32
        self.model = Qwen3TTSModel.from_pretrained(
            self.model_path,
            device_map=self.device,
            dtype=dtype,
            attn_implementation=attention,
        )

    def synthesize(self, text: str, language: str, speaker: str) -> bytes:
        self.load()
        with self._lock, torch.inference_mode():
            wavs, sample_rate = self.model.generate_custom_voice(
                text=text,
                language=language,
                speaker=speaker,
            )
        output = io.BytesIO()
        sf.write(output, wavs[0], sample_rate, format="WAV", subtype="PCM_16")
        return output.getvalue()


def create_app(service: QwenTTSService, max_text_length: int = 800) -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify(
            {
                "ready": service.model is not None,
                "model_path": service.model_path,
                "device": service.device,
            }
        )

    @app.post("/synthesize")
    def synthesize():
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text", "")).strip()
        if not text:
            return jsonify({"error": "text is required"}), 400
        if len(text) > max_text_length:
            return jsonify({"error": f"text exceeds {max_text_length} characters"}), 400

        try:
            audio = service.synthesize(
                text=text,
                language=str(payload.get("language") or "Auto"),
                speaker=str(payload.get("speaker") or "Vivian"),
            )
        except Exception as exc:
            app.logger.exception("Qwen3-TTS synthesis failed")
            return jsonify({"error": str(exc)}), 500
        return Response(audio, mimetype="audio/wav", headers={"Cache-Control": "no-store"})

    return app


def parse_args():
    default_model = Path(__file__).resolve().parent.parent / "models" / "Qwen3-TTS-12Hz-0.6B-CustomVoice"
    parser = argparse.ArgumentParser(description="Qwen3-TTS internal service")
    parser.add_argument("--model-path", default=str(default_model))
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--lazy", action="store_true", help="Load the model on the first synthesis request")
    return parser.parse_args()


def main():
    args = parse_args()
    service = QwenTTSService(args.model_path, args.device)
    if not args.lazy:
        service.load()
        print("Qwen3-TTS model loaded.", flush=True)
    create_app(service).run(
        host=args.host,
        port=args.port,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


if __name__ == "__main__":
    main()
