# Quick Reference Guide - awebpage-to-pdf

## 🚀 Getting Started

### Start Services (Local Development)

```powershell
# Terminal 1 - API Service
.\scripts\run_api.ps1

# Terminal 2 - Worker Service
.\scripts\run_worker.ps1
```

### Docker Deployment

```bash
docker-compose up -d --build
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/pdf-jobs` | Submit conversion job |
| `GET` | `/v1/pdf-jobs/{job_id}` | Get job status |
| `GET` | `/v1/pdf-jobs/{job_id}/file` | Download PDF |
| `GET` | `/healthz` | Health check |

---

## 💻 Quick Commands

### PowerShell (Windows)

```powershell
# Submit job
$job = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/v1/pdf-jobs" `
  -ContentType "application/json" `
  -Body '{"url": "https://example.com"}'

# Check status
Invoke-RestMethod -Uri "http://localhost:8000/v1/pdf-jobs/$($job.job_id)"

# Download PDF
Invoke-WebRequest `
  -Uri "http://localhost:8000/v1/pdf-jobs/$($job.job_id)/file" `
  -OutFile "output.pdf"

# Open PDF
Start-Process output.pdf
```

### cURL (Linux/Mac)

```bash
# Submit job
JOB_ID=$(curl -X POST http://localhost:8000/v1/pdf-jobs \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' | jq -r '.job_id')

# Check status
curl http://localhost:8000/v1/pdf-jobs/$JOB_ID

# Download PDF
curl http://localhost:8000/v1/pdf-jobs/$JOB_ID/file -o output.pdf
```

### Python

```python
import requests

# Submit and wait
response = requests.post("http://localhost:8000/v1/pdf-jobs", 
                        json={"url": "https://example.com"})
job_id = response.json()["job_id"]

# Poll status
import time
while True:
    status = requests.get(f"http://localhost:8000/v1/pdf-jobs/{job_id}").json()
    if status["status"] in ["succeeded", "failed"]:
        break
    time.sleep(2)

# Download
if status["status"] == "succeeded":
    pdf = requests.get(f"http://localhost:8000/v1/pdf-jobs/{job_id}/file")
    open("output.pdf", "wb").write(pdf.content)
```

---

## 🔧 Testing

```powershell
# Run all tests
.\scripts\run_tests.ps1

# Unit tests only
.\scripts\run_unit_tests.ps1

# Integration tests only
.\scripts\run_integration_tests.ps1
```

---

## 📊 Job Statuses

| Status | Meaning |
|--------|---------|
| `queued` | Waiting to process |
| `waiting_domain_lock` | Blocked by another job on same domain |
| `running` | Currently processing |
| `succeeded` | ✅ PDF ready for download |
| `failed` | ❌ Job failed (check error_code) |

---

## ⚙️ Configuration (.env)

```env
# Essential Settings
SQLITE_DB_PATH=./data/app.db
PDF_STORAGE_PATH=./data/pdfs
DEFAULT_RENDER_MODE=print_to_pdf

# Timeouts (seconds)
NAVIGATION_TIMEOUT_SECONDS=45
JOB_TIMEOUT_SECONDS=120
MAX_DOMAIN_WAIT_SECONDS=600

# Cleanup (seconds)
CLEANUP_INTERVAL_SECONDS=3600
CLEANUP_FILE_AGE_SECONDS=3600
```

---

## 🐛 Troubleshooting

### Service won't start
```powershell
# Check if port is in use
netstat -ano | findstr :8000

# Restart services
# Press Ctrl+C in terminals, then restart
```

### Job stuck in "running"
- Wait for timeout (default: 120s)
- Check worker logs
- Restart worker if needed

### PDF not found after success
- Download immediately (PDFs auto-delete after cleanup interval)
- Check `CLEANUP_FILE_AGE_SECONDS` setting

### Tests failing
```powershell
# Reinstall dependencies
uv sync

# Reinstall Playwright
uv run playwright install chromium
```

---

## 📁 Project Structure

```
awebpage-to-pdf/
├── src/app/           # Application code
│   ├── api/          # FastAPI endpoints
│   ├── worker/       # Worker & rendering
│   ├── queue/        # Queue service
│   └── security/     # URL validation
├── tests/            # Test suite
├── scripts/          # PowerShell scripts
├── docs/             # Documentation
├── data/             # SQLite DB & PDFs
└── .env              # Configuration
```

---

## 🔗 Documentation Links

- **[API Documentation](./API_DOCUMENTATION.md)** - Complete API reference
- **[n8n Integration](./N8N_INTEGRATION.md)** - Workflow automation guide
- **[Deployment Guide](./DEPLOYMENT.md)** - Production deployment
- **[README](../README.md)** - Project overview

---

## 📞 Common Issues

**Q: How do I change the port?**  
A: Edit `.env` → `API_PORT=8080`, restart API service

**Q: How do I increase timeouts?**  
A: Edit `.env` → Adjust `*_TIMEOUT_SECONDS` values, restart services

**Q: Can I process multiple domains in parallel?**  
A: Yes! Different domains process in parallel, same domain serializes

**Q: How do I monitor the service?**  
A: Check logs in terminals or use `docker-compose logs -f`

---

## 🎯 Example Workflow

```powershell
# 1. Start services
.\scripts\run_api.ps1  # Terminal 1
.\scripts\run_worker.ps1  # Terminal 2

# 2. Submit job
$job = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/v1/pdf-jobs" `
  -ContentType "application/json" `
  -Body '{"url": "https://example.com"}'

Write-Host "Job ID: $($job.job_id)" -ForegroundColor Green

# 3. Wait and check (repeat until succeeded)
Start-Sleep -Seconds 5
$status = Invoke-RestMethod -Uri "http://localhost:8000/v1/pdf-jobs/$($job.job_id)"
Write-Host "Status: $($status.status)" -ForegroundColor Cyan

# 4. Download PDF
Invoke-WebRequest `
  -Uri "http://localhost:8000/v1/pdf-jobs/$($job.job_id)/file" `
  -OutFile "my-pdf.pdf"

# 5. Open PDF
Start-Process my-pdf.pdf
```

---

## 🔐 Security Notes

- Only `http` and `https` URLs allowed
- Private IPs blocked (10.x, 192.168.x, 127.x)
- Metadata endpoints blocked (169.254.169.254)
- No authentication in v1.0 (add reverse proxy for auth)

---

## 📈 Performance Tips

1. **Batch by domain** - Process different domains in parallel
2. **Download promptly** - PDFs auto-delete after cleanup interval
3. **Adjust timeouts** - Increase for slow-loading pages
4. **Monitor disk** - PDFs can accumulate if cleanup disabled

---

## 🆘 Emergency Commands

```powershell
# Stop all services
# Press Ctrl+C in both terminals

# Kill stuck processes (if needed)
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force

# Clean up data
Remove-Item -Recurse -Force .\data\pdfs\*
Remove-Item .\data\app.db

# Fresh start
.\scripts\run_api.ps1
.\scripts\run_worker.ps1
```
