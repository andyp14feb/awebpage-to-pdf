# Run Worker service locally
# Usage: .\scripts\run_worker.ps1

Write-Host "Starting Worker service..." -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# Ensure Playwright is installed
Write-Host "Checking Playwright installation..." -ForegroundColor Yellow
uv run playwright install chromium

# Run Worker with uv
uv run python -m app.worker.main
