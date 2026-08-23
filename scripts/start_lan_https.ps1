$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$certificate = Join-Path $projectRoot ".cert\lan-cert.pem"
$privateKey = Join-Path $projectRoot ".cert\lan-key.pem"

if (-not (Test-Path -LiteralPath $certificate) -or -not (Test-Path -LiteralPath $privateKey)) {
    throw "LAN certificate is missing. Generate .cert/lan-cert.pem and .cert/lan-key.pem with mkcert first."
}

$env:VITE_HTTPS = "1"
$env:VITE_PORT = "8443"

Write-Host "Starting trusted LAN HTTPS on port 8443."
Write-Host "The phone must trust frontend/public/qwen-local-rootCA.cer before opening the HTTPS URL."
Push-Location (Join-Path $projectRoot "frontend")
try {
    yarn build
    if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
    yarn vite preview --host 0.0.0.0 --strictPort
} finally {
    Pop-Location
}
