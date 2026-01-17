# Run API service locally
# Usage: .\scripts\run_api.ps1

Write-Host "Starting API service..." -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# Run API with uv
uv run python -m app.api.main
