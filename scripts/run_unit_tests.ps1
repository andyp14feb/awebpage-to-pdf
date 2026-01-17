# Run unit tests only
# Usage: .\scripts\run_unit_tests.ps1

Write-Host "Running unit tests..." -ForegroundColor Green

uv run pytest tests/unit -v

Write-Host "`nUnit tests completed!" -ForegroundColor Green
