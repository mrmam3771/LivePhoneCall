$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is not installed or docker.exe is not on PATH."
}

docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker Desktop is not running." }

$requiredModels = @(
    "models\Qwen3-ASR-0.6B\config.json",
    "models\Qwen3-TTS-12Hz-0.6B-CustomVoice\config.json"
)
foreach ($model in $requiredModels) {
    if (-not (Test-Path -LiteralPath $model)) { throw "Required model is missing: $model" }
}

New-Item -ItemType Directory -Force -Path data, .cert | Out-Null
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.docker.example" -Destination ".env"
    Write-Host "Created .env from .env.docker.example."
}
docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker cannot access the NVIDIA GPU. Enable Docker Desktop's WSL2 engine and update the Windows NVIDIA driver."
}

docker compose up --build --detach
if ($LASTEXITCODE -ne 0) { throw "Docker Compose deployment failed." }

Write-Host "Qwen Voice is starting. Model loading can take several minutes."
Write-Host "Open the host port configured in .env after 'docker compose ps' reports healthy."
Write-Host "Use 'docker compose logs -f app' to follow startup."
