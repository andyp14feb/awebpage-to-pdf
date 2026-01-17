# Deployment Guide - awebpage-to-pdf

This guide covers deploying the service to production environments.

---

## Deployment Options

1. **Docker Compose** (Recommended for single server)
2. **Docker Swarm** (For multi-server setups)
3. **Kubernetes** (For enterprise deployments)
4. **Systemd Services** (Direct installation on Linux)

---

## Option 1: Docker Compose (Recommended)

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- 10GB disk space

### Deployment Steps

#### 1. Clone Repository

```bash
git clone <repository-url>
cd alburaq__download_visa
```

#### 2. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit configuration
```

**Production Configuration:**

```env
# Database
SQLITE_DB_PATH=/data/app.db

# Storage
PDF_STORAGE_PATH=/data/pdfs

# Render
DEFAULT_RENDER_MODE=print_to_pdf

# Timeouts (adjust based on your needs)
NAVIGATION_TIMEOUT_SECONDS=60
JOB_TIMEOUT_SECONDS=180
MAX_DOMAIN_WAIT_SECONDS=900

# Retry
MAX_RETRIES=3

# Cleanup (1 hour = 3600 seconds)
CLEANUP_INTERVAL_SECONDS=3600
CLEANUP_FILE_AGE_SECONDS=3600

# API
API_HOST=0.0.0.0
API_PORT=8000

# Worker
WORKER_POLL_INTERVAL_SECONDS=2

# Logging
LOG_LEVEL=INFO
```

#### 3. Build and Start Services

```bash
docker-compose up -d --build
```

#### 4. Verify Deployment

```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs -f

# Test health endpoint
curl http://localhost:8000/healthz
```

#### 5. Monitor Services

```bash
# View API logs
docker-compose logs -f api

# View Worker logs
docker-compose logs -f worker

# Check resource usage
docker stats
```

---

## Option 2: Systemd Services (Linux)

### Prerequisites

- Ubuntu 20.04+ or similar Linux distribution
- Python 3.11+
- Chromium browser dependencies

### Installation Steps

#### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    chromium-browser \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2
```

#### 2. Create Service User

```bash
sudo useradd -r -s /bin/false pdf-service
```

#### 3. Install Application

```bash
sudo mkdir -p /opt/pdf-service
sudo chown pdf-service:pdf-service /opt/pdf-service
cd /opt/pdf-service

# Clone repository
sudo -u pdf-service git clone <repository-url> .

# Create virtual environment
sudo -u pdf-service python3.11 -m venv venv
sudo -u pdf-service venv/bin/pip install -e .

# Install Playwright browsers
sudo -u pdf-service venv/bin/playwright install chromium
```

#### 4. Configure Environment

```bash
sudo -u pdf-service cp .env.example .env
sudo -u pdf-service nano .env
```

#### 5. Create Systemd Service Files

**API Service:** `/etc/systemd/system/pdf-api.service`

```ini
[Unit]
Description=PDF Conversion API Service
After=network.target

[Service]
Type=simple
User=pdf-service
Group=pdf-service
WorkingDirectory=/opt/pdf-service
Environment="PATH=/opt/pdf-service/venv/bin"
ExecStart=/opt/pdf-service/venv/bin/python -m app.api.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Worker Service:** `/etc/systemd/system/pdf-worker.service`

```ini
[Unit]
Description=PDF Conversion Worker Service
After=network.target pdf-api.service

[Service]
Type=simple
User=pdf-service
Group=pdf-service
WorkingDirectory=/opt/pdf-service
Environment="PATH=/opt/pdf-service/venv/bin"
ExecStart=/opt/pdf-service/venv/bin/python -m app.worker.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 6. Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable pdf-api pdf-worker
sudo systemctl start pdf-api pdf-worker

# Check status
sudo systemctl status pdf-api pdf-worker

# View logs
sudo journalctl -u pdf-api -f
sudo journalctl -u pdf-worker -f
```

---

## Reverse Proxy Setup (Nginx)

### Install Nginx

```bash
sudo apt install nginx
```

### Configure Nginx

Create `/etc/nginx/sites-available/pdf-service`:

```nginx
server {
    listen 80;
    server_name pdf.yourdomain.com;

    # Increase timeouts for long-running jobs
    proxy_connect_timeout 300;
    proxy_send_timeout 300;
    proxy_read_timeout 300;
    send_timeout 300;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Increase max body size for large requests
    client_max_body_size 10M;
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/pdf-service /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Add SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d pdf.yourdomain.com
```

---

## Production Checklist

### Security

- [ ] Configure firewall (allow only ports 80, 443)
- [ ] Enable SSL/TLS
- [ ] Implement rate limiting (nginx)
- [ ] Add authentication if needed
- [ ] Regular security updates

### Monitoring

- [ ] Set up log aggregation (ELK, Loki, etc.)
- [ ] Configure alerts for service failures
- [ ] Monitor disk usage (PDFs can accumulate)
- [ ] Track job success/failure rates
- [ ] Monitor API response times

### Backup

- [ ] Backup SQLite database regularly
- [ ] Consider external storage for PDFs
- [ ] Backup configuration files
- [ ] Document recovery procedures

### Performance

- [ ] Tune cleanup intervals based on usage
- [ ] Adjust worker poll interval
- [ ] Monitor memory usage
- [ ] Scale horizontally if needed

---

## Scaling Considerations

### Current Limitations

- Single worker (sequential processing)
- SQLite (single-server only)
- Local file storage

### Future Scaling Options

1. **Multiple Workers** (requires code changes)
   - Shared database (PostgreSQL)
   - Distributed locking (Redis)

2. **Object Storage** (S3, MinIO)
   - Replace local file storage
   - Better for multi-server deployments

3. **Load Balancing**
   - Multiple API instances
   - Shared worker pool

---

## Maintenance

### Log Rotation

Configure logrotate for systemd services:

`/etc/logrotate.d/pdf-service`:

```
/var/log/pdf-service/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 pdf-service pdf-service
    sharedscripts
    postrotate
        systemctl reload pdf-api pdf-worker
    endscript
}
```

### Database Maintenance

```bash
# Vacuum SQLite database (monthly)
sqlite3 /opt/pdf-service/data/app.db "VACUUM;"

# Check database integrity
sqlite3 /opt/pdf-service/data/app.db "PRAGMA integrity_check;"
```

### Updates

```bash
cd /opt/pdf-service
sudo -u pdf-service git pull
sudo -u pdf-service venv/bin/pip install -e .
sudo systemctl restart pdf-api pdf-worker
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u pdf-api -n 50
sudo journalctl -u pdf-worker -n 50

# Check permissions
ls -la /opt/pdf-service/data

# Verify Python environment
sudo -u pdf-service /opt/pdf-service/venv/bin/python --version
```

### High Memory Usage

```bash
# Check process memory
ps aux | grep python

# Restart worker
sudo systemctl restart pdf-worker
```

### Disk Space Issues

```bash
# Check disk usage
df -h

# Manual cleanup
find /opt/pdf-service/data/pdfs -type f -mtime +1 -delete

# Adjust cleanup settings in .env
```

---

## Support

For deployment issues:
- Check service logs
- Verify all dependencies installed
- Ensure correct permissions
- Review configuration files
