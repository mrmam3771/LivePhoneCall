# Qwen3 Voice Agent

Local Chinese/English voice-agent test bench built from Qwen3-ASR 0.6B,
Qwen3-TTS 0.6B CustomVoice, and LangChain. ASR and TTS use separate uv
environments because their upstream packages pin incompatible `transformers`
patch versions. All clients use the single public web port `8000`; the TTS
process listens internally on `localhost:8001`.

The start script limits ASR to a 16K context so both models fit concurrently in
the tested 16GB GPU. Increasing this value can prevent vLLM from allocating its
KV cache while TTS is resident.

## Install

From PowerShell, sync the Linux ASR/LangChain environment and isolated TTS environment:

```powershell
wsl bash -lc 'cd /mnt/d/1AProject/demo_list/ai/tts && UV_PROJECT_ENVIRONMENT=.venv-wsl uv sync --locked'
wsl bash -lc 'cd /mnt/d/1AProject/demo_list/ai/tts/qwen3-tts-service && uv sync'
```

Do not run the root `uv sync` on native Windows: vLLM currently requires Linux.
The installed Windows CUDA driver is shared with WSL, so inference still runs on
the same NVIDIA GPU.

Download Qwen3-TTS from ModelScope:

```powershell
wsl bash -lc 'cd /mnt/d/1AProject/demo_list/ai/tts && uv run --project qwen3-tts-service qwen3-tts-service/download_model.py'
```

## LangChain model

Without configuration, the page uses an explicit echo response so ASR and TTS
can be tested without an API key. The included provider is `langchain-openai`;
configure an OpenAI or OpenAI-compatible model before starting:

```text
VOICE_AGENT_MODEL=openai:gpt-4.1-mini
VOICE_AGENT_API_KEY=your-key
```

An OpenAI-compatible Qwen endpoint can also use `VOICE_AGENT_BASE_URL` and a
model such as `VOICE_AGENT_MODEL=openai:qwen-plus`. Optional settings are
`VOICE_AGENT_SYSTEM_PROMPT`, `VOICE_AGENT_TEMPERATURE`, `VOICE_AGENT_TIMEOUT`,
and `VOICE_AGENT_MAX_TOKENS`. Install the matching LangChain integration package
before selecting a different provider.

## Start

```powershell
wsl bash -lc 'cd /mnt/d/1AProject/demo_list/ai/tts && bash scripts/start_voice_agent.sh'
```

Open `http://127.0.0.1:8000`. The page supports microphone transcription,
turn-based Agent replies, automatic TTS playback, and direct TTS tests.

For mobile microphone testing, use a trusted HTTPS URL. A Cloudflare Quick
Tunnel is the shortest test path (no account required):

```powershell
winget install --id Cloudflare.cloudflared --exact
powershell -ExecutionPolicy Bypass -File scripts/start_mobile_https.ps1
```

Open the printed `https://*.trycloudflare.com` URL on the phone. A Quick Tunnel
is public, has a random address, and has no built-in authentication, so use it
only with non-sensitive test audio and stop it with `Ctrl+C` afterward. For
display or playback without microphone access, a phone on the same Wi-Fi can
use `http://<PC-LAN-IP>:8000` after allowing inbound TCP 8000 in Windows
Firewall. `localhost` on a phone means the phone itself.

```powershell
wsl bash -lc 'cd /mnt/d/1AProject/demo_list/ai/tts && bash scripts/stop_voice_agent.sh'
```

## API

- `GET /api/voice/health`: TTS readiness and LangChain configuration
- `POST /api/agent/chat`: `{ "text": "...", "conversation_id": "..." }`
- `POST /api/tts`: `{ "text": "...", "language": "Auto", "speaker": "Vivian" }`

`/api/tts` returns `audio/wav`. This is a turn-based browser call simulation,
not a PSTN/SIP carrier integration. The API boundary can later be reused from
Twilio, FreeSWITCH, or a mobile WebSocket gateway.
