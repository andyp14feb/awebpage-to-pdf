# awebpage-to-pdf

A robust, async job-based service for converting web pages to PDF documents. Designed for integration with automation tools like n8n.

## Features

- ✅ **Async Job Processing** - Submit URLs and poll for completion
- ✅ **Domain Serialization** - Prevents concurrent processing per domain (eTLD+1)
- ✅ **Deduplication** - Same URL on same day returns existing job
- ✅ **Two Render Modes** - `print_to_pdf` (default) and `screenshot_to_pdf`
- ✅ **SSRF Protection** - Blocks private IPs and metadata endpoints
- ✅ **Automatic Cleanup** - Removes old PDFs on schedule
- ✅ **SQLite Queue** - Simple, reliable job queue
- ✅ **Single Worker** - Predictable, sequential processing
- ✅ **Docker Ready** - Easy deployment with Docker Compose

## Architecture

- **API Service** (FastAPI) - Handles job submission, status, and downloads
- **Worker Service** (Playwright) - Renders web pages to PDF
- **SQLite Database** - Job queue and coordination
- **Local Storage** - Temporary PDF storage with cleanup

## Quick Start

### Prerequisites

- Python 3.11+
- `uv` package manager
- Docker Desktop (for containerized deployment)

### Local Development (Windows)

1. **Clone and setup**
   ```powershell
   git clone <repository>
   cd alburaq__download_visa
   ```

2. **Install dependencies**
   ```powershell
   uv venv
   uv sync
   ```

3. **Configure environment**
   ```powershell
   cp .env.example .env
   # Edit .env as needed
   ```

4. **Install Playwright browsers**
   ```powershell
   uv run playwright install chromium
   ```

5. **Run API service** (Terminal 1)
   ```powershell
   .\scripts\run_api.ps1
   ```

6. **Run Worker service** (Terminal 2)
   ```powershell
   .\scripts\run_worker.ps1
   ```

7. **API available at** `http://localhost:8000`

### Docker Deployment

1. **Build and run**
   ```bash
   docker-compose up --build
   ```

2. **API available at** `http://localhost:8000`

## API Usage

### Submit Job

```bash
POST /v1/pdf-jobs
Content-Type: application/json

{
  "url": "https://example.com",
  "render_mode": "print_to_pdf",
  "max_domain_wait_seconds": 600,
  "navigation_timeout_seconds": 45,
  "job_timeout_seconds": 120,
  "max_retries": 2,
  "metadata": {
    "source": "n8n",
    "reference_id": "optional"
  }
}
```

**Response (202 Accepted)**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "deduplicated": false
}
```

### Get Job Status

```bash
GET /v1/pdf-jobs/{job_id}
```

**Response**
```json
{
  "job_id": "uuid",
  "status": "succeeded",
  "attempts": 1,
  "created_at": "2024-01-17T00:00:00Z",
  "started_at": "2024-01-17T00:00:05Z",
  "finished_at": "2024-01-17T00:00:15Z",
  "error_code": null,
  "error_message": null,
  "deduplicated": false
}
```

**Job Statuses**
- `queued` - Waiting to be processed
- `waiting_domain_lock` - Blocked by another job on same domain
- `running` - Currently being processed
- `succeeded` - PDF generated successfully
- `failed` - Job failed (see error_code)

### Download PDF

```bash
GET /v1/pdf-jobs/{job_id}/file
```

Returns PDF file (only when status is `succeeded`)

### Health Check

```bash
GET /healthz
```

## Configuration

All settings can be configured via `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `SQLITE_DB_PATH` | `./data/app.db` | SQLite database path |
| `PDF_STORAGE_PATH` | `./data/pdfs` | PDF storage directory |
| `DEFAULT_RENDER_MODE` | `print_to_pdf` | Default render mode |
| `NAVIGATION_TIMEOUT_SECONDS` | `45` | Page load timeout |
| `JOB_TIMEOUT_SECONDS` | `120` | Total job timeout |
| `MAX_DOMAIN_WAIT_SECONDS` | `600` | Max wait for domain lock |
| `MAX_RETRIES` | `2` | Retry attempts |
| `CLEANUP_INTERVAL_SECONDS` | `1020` | Cleanup run frequency |
| `CLEANUP_FILE_AGE_SECONDS` | `1020` | File deletion threshold |

## Testing

### Run all tests
```powershell
.\scripts\run_tests.ps1
```

### Run unit tests only
```powershell
.\scripts\run_unit_tests.ps1
```

### Run integration tests only
```powershell
.\scripts\run_integration_tests.ps1
```

## Project Structure

```
awebpage-to-pdf/
├── src/
│   └── app/
│       ├── api/              # FastAPI endpoints
│       ├── worker/           # Worker and rendering
│       ├── queue/            # Queue service
│       ├── security/         # URL validation, SSRF
│       ├── utils/            # Domain extraction
│       ├── config.py         # Configuration
│       ├── database.py       # Database setup
│       └── models.py         # SQLAlchemy models
├── tests/
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # End-to-end tests
├── scripts/                  # PowerShell scripts
├── planning_docs/            # Design documents
├── docker-compose.yml        # Docker Compose config
├── Dockerfile.api            # API Dockerfile
├── Dockerfile.worker         # Worker Dockerfile
├── pyproject.toml            # Dependencies
└── .env.example              # Configuration template
```

## Key Design Decisions

### Domain Serialization (eTLD+1)
Jobs are serialized by **main domain** (eTLD+1), meaning:
- `a.example.com` and `b.example.com` → both map to `example.com`
- Only one job per main domain runs at a time
- Prevents overloading target websites

### Single Worker
- Exactly **1 worker** processes jobs sequentially
- Simplifies coordination and resource management
- Suitable for ~600 jobs/day workload

### Deduplication
- Same **normalized URL** + same **UTC date** → reuses existing job
- Prevents duplicate work from automation tools

### Temporary Storage
- PDFs stored locally with aggressive cleanup
- Files deleted after configured age threshold
- Not designed for long-term archival

## Security

- **SSRF Protection** - Blocks private IPs, localhost, metadata endpoints
- **URL Validation** - Only http/https schemes allowed
- **Redirect Validation** - Validates all redirect targets
- **Timeout Enforcement** - Hard limits on job execution time

## Troubleshooting

### Worker not processing jobs
- Check worker logs for errors
- Ensure Playwright browsers are installed: `uv run playwright install chromium`
- Verify database is accessible

### Jobs stuck in waiting_domain_lock
- Another job on same domain is running
- Check `max_domain_wait_seconds` configuration
- Review domain lock table in database

### PDF file not found
- Files may have been cleaned up
- Check `cleanup_file_age_seconds` setting
- Download PDFs immediately after completion

## Documentation

### 📚 Complete Documentation Guide

Choose the right documentation for your needs:

#### 🚀 **Getting Started**
- **[README.md](./README.md)** (this file) - Quick overview and setup
- **[Quick Reference](./docs/QUICK_REFERENCE.md)** - Fast command lookup and common tasks

#### 📡 **API Integration**
- **[API Documentation](./docs/API_DOCUMENTATION.md)** - Complete API reference
  - All endpoints with parameters
  - Request/response examples
  - Code samples (PowerShell, Python, JavaScript, cURL)
  - Error codes and troubleshooting

#### 🔄 **Workflow Automation**
- **[n8n Integration Guide](./docs/N8N_INTEGRATION.md)** - Workflow automation
  - Step-by-step n8n setup
  - Importable workflow JSON
  - Common use cases (invoice archival, reports)
  - Advanced patterns and best practices

#### 🚀 **Production Deployment**
- **[Deployment Guide](./docs/DEPLOYMENT.md)** - Production setup
  - Docker Compose deployment
  - Systemd services (Linux)
  - Nginx reverse proxy
  - SSL/TLS configuration
  - Monitoring and maintenance

#### 📋 **Planning & Design**
See `planning_docs/` for original specifications:
- `PRD__v1_1.md` - Product requirements
- `FSD__v1_1.md` - Functional specification
- `Engineering_Plan__v1_1.md` - Engineering plan
- `00_dev_kickstart_windows_uv_tests.md` - Developer guide

---

### 🎯 Which Documentation Should I Read?

| I want to... | Read this |
|--------------|-----------|
| Get started quickly | [README.md](./README.md) + [Quick Reference](./docs/QUICK_REFERENCE.md) |
| Integrate with my app | [API Documentation](./docs/API_DOCUMENTATION.md) |
| Use with n8n | [n8n Integration Guide](./docs/N8N_INTEGRATION.md) |
| Deploy to production | [Deployment Guide](./docs/DEPLOYMENT.md) |
| Find a specific command | [Quick Reference](./docs/QUICK_REFERENCE.md) |
| Understand the design | `planning_docs/` directory |
| Troubleshoot an issue | [Quick Reference](./docs/QUICK_REFERENCE.md) → Troubleshooting section |

## License

MIT License
