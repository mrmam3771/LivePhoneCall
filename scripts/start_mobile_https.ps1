$ErrorActionPreference = "Stop"

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw "cloudflared is missing. Install it with: winget install --id Cloudflare.cloudflared --exact"
}

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/voice/health" -TimeoutSec 5 | Out-Null
} catch {
    throw "The voice agent is not ready at http://127.0.0.1:8000. Start it first."
}

Write-Warning "This creates a public, unauthenticated test URL. Stop it with Ctrl+C after testing."
cloudflared tunnel --url http://127.0.0.1:8000
