# n8n Integration Guide - awebpage-to-pdf

This guide shows how to integrate the awebpage-to-pdf service with n8n workflows.

---

## Prerequisites

- n8n installed and running
- Webpage-to-PDF service running (API accessible)
- Basic knowledge of n8n workflows

---

## Quick Start Workflow

### Workflow Overview

```
Trigger → Submit PDF Job → Wait → Check Status → Download PDF → Upload to Google Drive
```

---

## Step-by-Step Setup

### 1. Submit PDF Conversion Job

**Node Type:** HTTP Request

**Configuration:**
- **Method:** POST
- **URL:** `http://localhost:8000/v1/pdf-jobs`
- **Authentication:** None
- **Body Content Type:** JSON
- **Specify Body:** Using JSON

**Body (JSON):**
```json
{
  "url": "{{ $json.url }}",
  "metadata": {
    "source": "n8n",
    "workflow_id": "{{ $workflow.id }}",
    "execution_id": "{{ $execution.id }}"
  }
}
```

**Output:**
- `job_id` - Use this to track the job
- `status` - Initial status (usually "queued")
- `deduplicated` - Whether this is a duplicate submission

---

### 2. Wait for Processing

**Node Type:** Wait

**Configuration:**
- **Resume:** After time interval
- **Wait Amount:** 5 seconds

This gives the worker time to start processing.

---

### 3. Poll Job Status (Loop)

**Node Type:** HTTP Request (in a loop)

**Configuration:**
- **Method:** GET
- **URL:** `http://localhost:8000/v1/pdf-jobs/{{ $json.job_id }}`
- **Authentication:** None

**Add Loop Logic:**

Use an **IF** node to check status:

```javascript
// Check if job is complete
{{ $json.status === 'succeeded' || $json.status === 'failed' }}
```

- **True:** Continue to download
- **False:** Wait 2 seconds and check again

---

### 4. Download PDF

**Node Type:** HTTP Request

**Configuration:**
- **Method:** GET
- **URL:** `http://localhost:8000/v1/pdf-jobs/{{ $json.job_id }}/file`
- **Response Format:** File
- **Binary Property:** `data`

**Output:**
- Binary PDF file in `data` property

---

### 5. Upload to Google Drive

**Node Type:** Google Drive

**Configuration:**
- **Operation:** Upload
- **Binary Property:** `data`
- **File Name:** `{{ $json.job_id }}.pdf` or custom name
- **Folder:** Select destination folder

---

## Complete n8n Workflow (JSON)

Here's a complete workflow you can import into n8n:

```json
{
  "name": "Webpage to PDF to Google Drive",
  "nodes": [
    {
      "parameters": {
        "url": "={{ $json.url }}",
        "method": "POST",
        "bodyParametersJson": "={\n  \"url\": \"{{ $json.url }}\",\n  \"metadata\": {\n    \"source\": \"n8n\",\n    \"workflow_id\": \"{{ $workflow.id }}\"\n  }\n}",
        "options": {}
      },
      "name": "Submit PDF Job",
      "type": "n8n-nodes-base.httpRequest",
      "position": [250, 300],
      "typeVersion": 4.1
    },
    {
      "parameters": {
        "amount": 5,
        "unit": "seconds"
      },
      "name": "Wait",
      "type": "n8n-nodes-base.wait",
      "position": [450, 300],
      "typeVersion": 1
    },
    {
      "parameters": {
        "url": "=http://localhost:8000/v1/pdf-jobs/{{ $json.job_id }}",
        "options": {}
      },
      "name": "Check Status",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 300],
      "typeVersion": 4.1
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.status }}",
              "operation": "equals",
              "value2": "succeeded"
            }
          ]
        }
      },
      "name": "If Succeeded",
      "type": "n8n-nodes-base.if",
      "position": [850, 300],
      "typeVersion": 1
    },
    {
      "parameters": {
        "url": "=http://localhost:8000/v1/pdf-jobs/{{ $json.job_id }}/file",
        "responseFormat": "file",
        "options": {}
      },
      "name": "Download PDF",
      "type": "n8n-nodes-base.httpRequest",
      "position": [1050, 200],
      "typeVersion": 4.1
    },
    {
      "parameters": {
        "operation": "upload",
        "fileContent": "data",
        "name": "={{ $json.job_id }}.pdf",
        "driveId": {
          "__rl": true,
          "mode": "list",
          "value": "My Drive"
        },
        "folderId": {
          "__rl": true,
          "mode": "list",
          "value": "root"
        }
      },
      "name": "Upload to Google Drive",
      "type": "n8n-nodes-base.googleDrive",
      "position": [1250, 200],
      "typeVersion": 3
    }
  ],
  "connections": {
    "Submit PDF Job": {
      "main": [[{ "node": "Wait", "type": "main", "index": 0 }]]
    },
    "Wait": {
      "main": [[{ "node": "Check Status", "type": "main", "index": 0 }]]
    },
    "Check Status": {
      "main": [[{ "node": "If Succeeded", "type": "main", "index": 0 }]]
    },
    "If Succeeded": {
      "main": [
        [{ "node": "Download PDF", "type": "main", "index": 0 }],
        [{ "node": "Wait", "type": "main", "index": 0 }]
      ]
    },
    "Download PDF": {
      "main": [[{ "node": "Upload to Google Drive", "type": "main", "index": 0 }]]
    }
  }
}
```

---

## Advanced Patterns

### Batch Processing Multiple URLs

**Use Case:** Convert multiple URLs from a spreadsheet

```
Read Google Sheet → Split In Batches → Submit PDF Job → Loop Status Check → Download → Upload
```

**Configuration:**
- Use **Split In Batches** node to process URLs one at a time
- This respects domain serialization (one domain at a time)

---

### Error Handling

Add error handling for failed jobs:

**IF Node - Check for Failure:**
```javascript
{{ $json.status === 'failed' }}
```

**Then:**
- Send notification (Slack, Email, etc.)
- Log error to database
- Retry with different settings

---

### Custom Filenames

Generate meaningful filenames from URL:

**Function Node:**
```javascript
const url = $input.item.json.url;
const domain = new URL(url).hostname;
const timestamp = new Date().toISOString().split('T')[0];
const filename = `${domain}_${timestamp}.pdf`;

return {
  json: {
    ...item.json,
    filename: filename
  }
};
```

Use in Google Drive upload:
```
File Name: {{ $json.filename }}
```

---

### Webhook Trigger

Trigger PDF conversion via webhook:

**Webhook Node:**
- **Path:** `/convert-to-pdf`
- **Method:** POST
- **Response Mode:** When Last Node Finishes

**Expected Payload:**
```json
{
  "url": "https://example.com",
  "destination_folder": "folder_id"
}
```

---

## Performance Tips

### 1. Batch Processing Strategy

Process URLs from different domains in parallel:

```
Split URLs by Domain → Process Each Domain Sequentially → Merge Results
```

### 2. Optimal Polling Interval

- **First check:** After 5 seconds
- **Subsequent checks:** Every 2-3 seconds
- **Max wait:** 2-3 minutes (then fail)

### 3. Deduplication Awareness

Check `deduplicated` flag to avoid re-downloading:

```javascript
if ($json.deduplicated === true) {
  // Job already exists, skip to download
  return { json: { job_id: $json.job_id } };
}
```

---

## Common Use Cases

### 1. Invoice Archival

```
Email Trigger → Extract Invoice URL → Convert to PDF → Upload to Google Drive → Send Confirmation
```

### 2. Report Generation

```
Schedule Trigger → Generate Report URL → Convert to PDF → Email PDF → Archive
```

### 3. Web Scraping to PDF

```
HTTP Request (Get URLs) → Loop URLs → Convert Each to PDF → Zip All PDFs → Upload
```

### 4. Form Submission Receipt

```
Webhook (Form Submit) → Generate Receipt Page → Convert to PDF → Email to User
```

---

## Troubleshooting

### Job Stays in "running" Status

**Solution:** Increase polling timeout or check worker logs

### "PDF file not found" Error

**Cause:** PDF was cleaned up before download

**Solution:** Download immediately after success, or increase cleanup interval

### Rate Limiting Issues

**Cause:** Too many jobs for same domain

**Solution:** 
- Batch by domain
- Add delays between submissions
- Increase `max_domain_wait_seconds`

---

## Example: Complete Invoice Processing Workflow

```javascript
// 1. Webhook receives invoice data
// Input: { invoice_url: "https://...", customer_email: "..." }

// 2. Submit to PDF service
POST http://localhost:8000/v1/pdf-jobs
Body: { "url": "{{ $json.invoice_url }}" }

// 3. Wait 5 seconds
Wait: 5 seconds

// 4. Poll status (loop until complete)
GET http://localhost:8000/v1/pdf-jobs/{{ $json.job_id }}
If status != "succeeded": Wait 2s and retry

// 5. Download PDF
GET http://localhost:8000/v1/pdf-jobs/{{ $json.job_id }}/file

// 6. Upload to Google Drive
Google Drive: Upload to "Invoices/{{ $now.format('YYYY/MM') }}"

// 7. Email customer
Email: Send PDF attachment to {{ $json.customer_email }}

// 8. Update database
Database: Mark invoice as processed
```

---

## Best Practices

1. **Always handle errors** - Check for `failed` status
2. **Download PDFs promptly** - Before cleanup runs
3. **Use metadata** - Track workflow and execution IDs
4. **Respect domain limits** - Don't overwhelm target sites
5. **Monitor job queue** - Watch for stuck jobs
6. **Set reasonable timeouts** - Based on typical page load times

---

## Support

For n8n-specific issues:
- Check n8n community forum
- Review n8n HTTP Request node documentation

For PDF service issues:
- Check API documentation
- Review worker logs
- Verify service is running
