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

## Model providers

Open `http://127.0.0.1:8000/settings` to configure and test providers without
restarting the service. The built-in catalog includes OpenAI, Anthropic, Google
Gemini, Alibaba DashScope, DeepSeek, Moonshot AI, OpenRouter, SiliconFlow, and
Ollama. Custom OpenAI-compatible endpoints such as vLLM and LM Studio can be
added from the same page.

The settings page and its mutation/test APIs accept localhost requests only.
They are intentionally unavailable through LAN addresses and the mobile HTTPS
tunnel so a remote client cannot redirect requests carrying a stored API key.

The design follows pi's separation of model configuration and authentication:
provider/model settings are saved in `.voice-agent/models.json`, while API keys
are saved separately in `.voice-agent/auth.json` and are never returned by the
settings API. Both files are ignored by Git. A blank key field preserves the
stored key.

### Environment fallback

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

Environment variables remain a backward-compatible fallback until the settings
page saves its first provider configuration. After that, the active provider in
the settings page takes precedence.

## Start

```powershell
wsl bash -lc 'cd /mnt/d/1AProject/demo_list/ai/tts && bash scripts/start_voice_agent.sh'
```

## Vue frontend

The new chat interface lives in `frontend/` as a Vue 3 and Vite application.
It includes responsive conversation navigation, text messages, browser audio
recording with microphone selection, IndexedDB persistence, custom Agents, and
light/dark themes. Each Agent can define its own instructions, provider, model,
language, and reply voice. Each conversation remains bound to the Agent it was
created with, and the active conversation's Agent can be changed from the
chat header at any time. The light palette uses cream and soft orange; the
dark palette uses charcoal and soft purple.

For frontend-only development, leave the AI services stopped and run:

```powershell
cd frontend
yarn
yarn dev
```

Open `http://127.0.0.1:8000`. Text and recorded audio are stored only in that
browser profile. Clearing site data removes them. This preview intentionally
does not call ASR, LLM, or TTS APIs yet.

Build and test the frontend with `yarn build` and `yarn test`. The next
integration step is to connect the Vue composer and phone workflow to the
existing `/api/*` endpoints, then serve the production bundle from Flask.

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
- `POST /api/agent/chat`: `{ "text": "...", "conversation_id": "...", "history": [...] }`
- `POST /api/tts`: `{ "text": "...", "language": "Auto", "speaker": "Vivian" }`
- `GET /api/settings`: provider catalog with credential status, never key values
- `PUT /api/settings/provider`: save a provider and optionally activate it
- `POST /api/settings/test`: test the saved provider connection

`/api/tts` returns `audio/wav`. This is a turn-based browser call simulation,
not a PSTN/SIP carrier integration. The API boundary can later be reused from
Twilio, FreeSWITCH, or a mobile WebSocket gateway.
