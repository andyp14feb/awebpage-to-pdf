# API Documentation - awebpage-to-pdf

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000` (or your deployment URL)

---

## Overview

The awebpage-to-pdf service provides a RESTful API for converting web pages to PDF documents. The service uses an asynchronous job-based architecture, allowing you to submit URLs and retrieve PDFs when ready.

### Key Features

- ✅ **Async Processing** - Submit jobs and poll for completion
- ✅ **Automatic Deduplication** - Same URL on same day returns existing job
- ✅ **Domain Rate Limiting** - Prevents overloading target websites
- ✅ **Two Render Modes** - Print-to-PDF or Screenshot-to-PDF
- ✅ **SSRF Protection** - Blocks private IPs and metadata endpoints
- ✅ **Configurable Timeouts** - Per-job timeout overrides

---

## Authentication

**Current Version:** No authentication required  
**Future:** API keys may be added in later versions

---

## Endpoints

### 1. Submit PDF Conversion Job

Submit a URL for PDF conversion.

**Endpoint:** `POST /v1/pdf-jobs`  
**Content-Type:** `application/json`

#### Request Body

```json
{
  "url": "https://example.com",
  "render_mode": "print_to_pdf",
  "navigation_timeout_seconds": 45,
  "job_timeout_seconds": 120,
  "max_domain_wait_seconds": 600,
  "max_retries": 2,
  "metadata": {
    "source": "n8n",
    "reference_id": "optional-id"
  }
}
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | **Yes** | - | URL to convert (http/https only) |
| `render_mode` | string | No | `print_to_pdf` | Render mode: `print_to_pdf` or `screenshot_to_pdf` |
| `navigation_timeout_seconds` | integer | No | 45 | Page load timeout (5-300) |
| `job_timeout_seconds` | integer | No | 120 | Total job timeout (10-600) |
| `max_domain_wait_seconds` | integer | No | 600 | Max wait for domain lock (10-3600) |
| `max_retries` | integer | No | 2 | Retry attempts (0-5) |
| `metadata` | object | No | null | Optional metadata (any JSON) |

#### Response

**Status:** `202 Accepted`

```json
{
  "job_id": "a23e18c7-9033-489a-bca2-d121ef61597c",
  "status": "queued",
  "deduplicated": false
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique job identifier (UUID) |
| `status` | string | Current job status |
| `deduplicated` | boolean | `true` if returning existing job for same URL today |

#### Error Responses

**400 Bad Request** - Invalid URL or SSRF blocked
```json
{
  "detail": "URL must use http or https scheme"
}
```

**500 Internal Server Error** - Server error
```json
{
  "error": "Internal server error",
  "detail": "Error message"
}
```

---

### 2. Get Job Status

Retrieve the current status of a job.

**Endpoint:** `GET /v1/pdf-jobs/{job_id}`

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Job ID from submit response |

#### Response

**Status:** `200 OK`

```json
{
  "job_id": "a23e18c7-9033-489a-bca2-d121ef61597c",
  "status": "succeeded",
  "attempts": 1,
  "created_at": "2026-01-17T04:08:42.815072",
  "started_at": "2026-01-17T04:08:44.436517",
  "finished_at": "2026-01-17T04:08:47.461832",
  "error_code": null,
  "error_message": null,
  "deduplicated": false
}
```

#### Job Statuses

| Status | Description |
|--------|-------------|
| `queued` | Job is waiting to be processed |
| `waiting_domain_lock` | Job is blocked by another job on same domain |
| `running` | Job is currently being processed |
| `succeeded` | PDF generated successfully |
| `failed` | Job failed (see `error_code` and `error_message`) |

#### Error Codes

| Code | Description |
|------|-------------|
| `DOMAIN_WAIT_TIMEOUT` | Exceeded max wait time for domain lock |
| `RENDER_FAILED` | Failed to render PDF after retries |
| `INVALID_URL` | URL format is invalid |
| `SSRF_BLOCKED` | URL blocked by SSRF protection |

#### Error Responses

**404 Not Found** - Job not found
```json
{
  "detail": "Job not found"
}
```

---

### 3. Download PDF File

Download the generated PDF file.

**Endpoint:** `GET /v1/pdf-jobs/{job_id}/file`

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | string | Job ID from submit response |

#### Response

**Status:** `200 OK`  
**Content-Type:** `application/pdf`

Returns the PDF file as binary data.

#### Error Responses

**400 Bad Request** - Job not completed
```json
{
  "detail": "Job not completed. Current status: running"
}
```

**404 Not Found** - Job not found or PDF deleted
```json
{
  "detail": "PDF file not found (may have been cleaned up)"
}
```

---

### 4. Health Check

Check if the API service is running.

**Endpoint:** `GET /healthz`

#### Response

**Status:** `200 OK`

```json
{
  "status": "healthy"
}
```

---

## Usage Examples

### cURL (Unix/Linux/Mac)

```bash
# Submit job
curl -X POST http://localhost:8000/v1/pdf-jobs \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Get status
curl http://localhost:8000/v1/pdf-jobs/{job_id}

# Download PDF
curl http://localhost:8000/v1/pdf-jobs/{job_id}/file -o output.pdf
```

### PowerShell (Windows)

```powershell
# Submit job
$response = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/v1/pdf-jobs" `
  -ContentType "application/json" `
  -Body '{"url": "https://example.com"}'

# Get status
Invoke-RestMethod -Uri "http://localhost:8000/v1/pdf-jobs/$($response.job_id)"

# Download PDF
Invoke-WebRequest `
  -Uri "http://localhost:8000/v1/pdf-jobs/$($response.job_id)/file" `
  -OutFile "output.pdf"
```

### Python

```python
import requests
import time

# Submit job
response = requests.post(
    "http://localhost:8000/v1/pdf-jobs",
    json={"url": "https://example.com"}
)
job_id = response.json()["job_id"]
print(f"Job ID: {job_id}")

# Poll for completion
while True:
    status_response = requests.get(
        f"http://localhost:8000/v1/pdf-jobs/{job_id}"
    )
    status = status_response.json()["status"]
    print(f"Status: {status}")
    
    if status in ["succeeded", "failed"]:
        break
    
    time.sleep(2)

# Download PDF if succeeded
if status == "succeeded":
    pdf_response = requests.get(
        f"http://localhost:8000/v1/pdf-jobs/{job_id}/file"
    )
    with open("output.pdf", "wb") as f:
        f.write(pdf_response.content)
    print("PDF downloaded!")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');
const fs = require('fs');

async function convertToPDF(url) {
  // Submit job
  const submitResponse = await axios.post(
    'http://localhost:8000/v1/pdf-jobs',
    { url: url }
  );
  const jobId = submitResponse.data.job_id;
  console.log(`Job ID: ${jobId}`);
  
  // Poll for completion
  while (true) {
    const statusResponse = await axios.get(
      `http://localhost:8000/v1/pdf-jobs/${jobId}`
    );
    const status = statusResponse.data.status;
    console.log(`Status: ${status}`);
    
    if (status === 'succeeded' || status === 'failed') {
      break;
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  // Download PDF
  const pdfResponse = await axios.get(
    `http://localhost:8000/v1/pdf-jobs/${jobId}/file`,
    { responseType: 'arraybuffer' }
  );
  fs.writeFileSync('output.pdf', pdfResponse.data);
  console.log('PDF downloaded!');
}

convertToPDF('https://example.com');
```

---

## Best Practices

### 1. Polling Strategy

**Recommended polling interval:** 2-5 seconds

```python
import time

def wait_for_completion(job_id, max_wait=300):
    """Poll job status until completion or timeout."""
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(f"http://localhost:8000/v1/pdf-jobs/{job_id}")
        status = response.json()["status"]
        
        if status in ["succeeded", "failed"]:
            return status
        
        time.sleep(2)  # Poll every 2 seconds
    
    raise TimeoutError("Job did not complete in time")
```

### 2. Error Handling

Always check job status before downloading:

```python
status_data = requests.get(f"http://localhost:8000/v1/pdf-jobs/{job_id}").json()

if status_data["status"] == "succeeded":
    # Download PDF
    pdf = requests.get(f"http://localhost:8000/v1/pdf-jobs/{job_id}/file")
    with open("output.pdf", "wb") as f:
        f.write(pdf.content)
elif status_data["status"] == "failed":
    print(f"Job failed: {status_data['error_message']}")
```

### 3. Deduplication Awareness

If you submit the same URL multiple times in a day, you'll get the same job_id:

```python
# First submission
job1 = requests.post("http://localhost:8000/v1/pdf-jobs", 
                     json={"url": "https://example.com"}).json()
# job1["deduplicated"] = False

# Second submission (same day)
job2 = requests.post("http://localhost:8000/v1/pdf-jobs",
                     json={"url": "https://example.com"}).json()
# job2["deduplicated"] = True
# job2["job_id"] == job1["job_id"]
```

### 4. Download PDFs Promptly

PDFs are automatically cleaned up after a configured time (default: 17 minutes). Download PDFs as soon as the job succeeds.

---

## Rate Limits & Constraints

### Domain Serialization

Only **one job per main domain** can run at a time. For example:
- `https://a.example.com` and `https://b.example.com` are treated as the same domain
- The second job will wait in `waiting_domain_lock` status until the first completes

### Timeouts

| Timeout | Default | Min | Max | Description |
|---------|---------|-----|-----|-------------|
| Navigation | 45s | 5s | 300s | Page load timeout |
| Job | 120s | 10s | 600s | Total job execution |
| Domain Wait | 600s | 10s | 3600s | Max wait for domain lock |

### Retries

- Default: 2 retry attempts
- Configurable: 0-5 retries per job
- Only transient failures are retried (timeouts, network errors)

---

## SSRF Protection

The service blocks requests to:
- Private IP ranges (10.x.x.x, 192.168.x.x, 172.16-31.x.x, 127.x.x.x)
- Localhost
- Metadata endpoints (169.254.169.254)
- Link-local addresses

Only `http` and `https` schemes are allowed.

---

## Troubleshooting

### Job Stuck in "running"

**Possible causes:**
- Page is taking longer than expected to load
- Worker crashed or was restarted
- Job timeout will eventually fail the job

**Solution:** Wait for job timeout or check worker logs

### Job Failed with "DOMAIN_WAIT_TIMEOUT"

**Cause:** Another job on the same domain is taking too long

**Solution:** 
- Increase `max_domain_wait_seconds`
- Wait and retry later
- Process different domains in parallel

### PDF Not Found After Success

**Cause:** PDF was cleaned up (default: after 17 minutes)

**Solution:** Download PDFs immediately after job succeeds

### "SSRF protection" Error

**Cause:** URL points to private/internal resource

**Solution:** Only submit public URLs

---

## Support

For issues or questions:
- Check worker logs for detailed error messages
- Review job `error_code` and `error_message` fields
- Ensure target website is publicly accessible

---

## Changelog

### Version 1.0.0 (2026-01-17)
- Initial release
- Async job-based architecture
- SQLite queue with domain locking
- Two render modes (print_to_pdf, screenshot_to_pdf)
- SSRF protection
- Deduplication support
