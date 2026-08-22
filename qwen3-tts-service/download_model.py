from pathlib import Path

from modelscope import snapshot_download


target = Path(__file__).resolve().parent.parent / "models" / "Qwen3-TTS-12Hz-0.6B-CustomVoice"
snapshot_download(
    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    local_dir=str(target),
)
print(target)
