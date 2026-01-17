# Run all tests
# Usage: .\scripts\run_tests.ps1

Write-Host "Running all tests..." -ForegroundColor Green

uv run pytest -v --cov=src --cov-report=html --cov-report=term

Write-Host "`nTest execution completed!" -ForegroundColor Green
Write-Host "Coverage report generated in htmlcov/index.html" -ForegroundColor Cyan
