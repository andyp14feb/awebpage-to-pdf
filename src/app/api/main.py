"""FastAPI application and endpoints."""
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone

from app.config import settings
from app.database import get_db, init_db
from app.queue.service import QueueService
from app.api.schemas import JobSubmitRequest, JobSubmitResponse, JobStatusResponse, ErrorResponse
from app.models import JobStatus, WorkerHeartbeat
from app.security.url_validator import SSRFError

from app.utils.logging import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Webpage-to-PDF Conversion Service",
    description="Async job-based webpage to PDF conversion service",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Webpage-to-PDF API service")
    settings.ensure_directories()
    init_db()
    logger.info("Database initialized")


@app.get("/healthz")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint with worker monitoring."""
    try:
        # Check database connection
        db.execute(select(1))
        
        # Check worker heartbeat
        worker_status = "unknown"
        heartbeat = db.get(WorkerHeartbeat, "worker-1")
        
        details = {}
        if heartbeat:
            # Ensure timezone awareness
            last_beat = heartbeat.last_heartbeat
            if last_beat.tzinfo is None:
                last_beat = last_beat.replace(tzinfo=timezone.utc)
                
            age = (datetime.now(timezone.utc) - last_beat).total_seconds()
            is_alive = age < 30  # Consider dead if validation older than 30s
            worker_status = "healthy" if is_alive else "stale"
            details = {
                "last_heartbeat": last_beat.isoformat(),
                "age_seconds": round(age, 1),
                "state": heartbeat.status,
                "current_job": heartbeat.current_job_id
            }
        else:
            worker_status = "missing"
            
        return {
            "status": "healthy" if worker_status == "healthy" else "degraded",
            "database": "connected",
            "worker": {
                "status": worker_status,
                **details
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.post("/v1/pdf-jobs", response_model=JobSubmitResponse, status_code=202)
async def submit_job(request: JobSubmitRequest, db: Session = Depends(get_db)):
    """
    Submit a new PDF conversion job.
    
    Returns:
        202 Accepted with job_id and status
    """
    try:
        job, deduplicated = QueueService.create_job(
            db=db,
            url=request.url,
            render_mode=request.render_mode,
            navigation_timeout_seconds=request.navigation_timeout_seconds,
            job_timeout_seconds=request.job_timeout_seconds,
            max_domain_wait_seconds=request.max_domain_wait_seconds,
            max_retries=request.max_retries,
            metadata=request.metadata
        )
        
        return JobSubmitResponse(
            job_id=job.job_id,
            status=job.status,
            deduplicated=deduplicated
        )
        
    except ValueError as e:
        logger.warning(f"Invalid URL submission: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except SSRFError as e:
        logger.warning(f"SSRF blocked: {e}")
        raise HTTPException(status_code=400, detail=f"SSRF protection: {str(e)}")
    except Exception as e:
        logger.error(f"Error submitting job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/v1/pdf-jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Get job status.
    
    Returns:
        Job status information
    """
    job = QueueService.get_job(db, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse.model_validate(job)


@app.get("/v1/pdf-jobs/{job_id}/file")
async def download_pdf(job_id: str, db: Session = Depends(get_db)):
    """
    Download PDF file for completed job.
    
    Returns:
        PDF file stream
    """
    job = QueueService.get_job(db, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.SUCCEEDED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed. Current status: {job.status}"
        )
    
    # Check if file exists
    pdf_path = Path(settings.pdf_storage_path) / f"{job_id}.pdf"
    
    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="PDF file not found (may have been cleaned up)"
        )
    
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{job_id}.pdf"
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False
    )
