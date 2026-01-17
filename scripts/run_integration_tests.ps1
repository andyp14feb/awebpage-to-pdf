# Run integration tests only
# Usage: .\scripts\run_integration_tests.ps1

Write-Host "Running integration tests..." -ForegroundColor Green

uv run pytest tests/integration -v

Write-Host "`nIntegration tests completed!" -ForegroundColor Green
