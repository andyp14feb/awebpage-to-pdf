"""Worker main loop for processing jobs."""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.database import get_db_context, init_db
from app.queue.service import QueueService
from app.worker.render import render_service
from app.models import Job
from app.security.url_validator import validate_redirects, SSRFError
from app.utils.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

from app.models import Job, WorkerHeartbeat
from app.database import get_db_context, init_db
from app.api import schemas

class Worker:
    """Worker for processing PDF conversion jobs."""
    
    def __init__(self):
        self.running = False
        self.current_job: Optional[Job] = None
        self.worker_id = "worker-1" # Single worker ID
    
    async def heartbeat_loop(self):
        """Background task to update worker heartbeat."""
        logger.info("Starting heartbeat loop")
        while self.running:
            try:
                with get_db_context() as db:
                    heartbeat = db.get(WorkerHeartbeat, self.worker_id)
                    if not heartbeat:
                        heartbeat = WorkerHeartbeat(worker_id=self.worker_id, last_heartbeat=datetime.now(timezone.utc))
                        db.add(heartbeat)
                    
                    heartbeat.last_heartbeat = datetime.now(timezone.utc)
                    heartbeat.status = "working" if self.current_job else "idle"
                    heartbeat.current_job_id = self.current_job.job_id if self.current_job else None
                    db.commit()
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
            
            await asyncio.sleep(10)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
from app.security.url_validator import validate_redirects, SSRFError

# ... (inside Worker class)

    async def process_job(self, job: Job) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Process a single job.
        
        Returns:
            Tuple of (success, error_code, error_message)
        """
        self.current_job = job
        
        logger.info(f"Processing job {job.job_id}: {job.normalized_url}")
        logger.info(f"  Render mode: {job.render_mode}")
        logger.info(f"  Attempt: {job.attempts}/{job.max_retries}")
        
        output_path = Path(settings.pdf_storage_path) / f"{job.job_id}.pdf"
        
        try:
            # Validate redirects first (SSRF protection)
            logger.info("Validating redirects...")
            final_url = await validate_redirects(job.normalized_url)
            logger.info(f"Redirect validation passed. Final URL: {final_url}")
            
            # Render with timeout
            await asyncio.wait_for(
                render_service.render_to_pdf(
                    url=final_url,  # Use validated final URL
                    output_path=output_path,
                    render_mode=job.render_mode,
                    navigation_timeout_seconds=job.navigation_timeout_seconds,
                    job_timeout_seconds=job.job_timeout_seconds
                ),
                timeout=job.job_timeout_seconds
            )
            
            logger.info(f"Job {job.job_id} completed successfully")
            return True, None, None
            
        except SSRFError as e:
            logger.error(f"Job {job.job_id} blocked by SSRF protection: {e}")
            return False, "SSRF_BLOCKED", str(e)
            
        except asyncio.TimeoutError:
            logger.error(f"Job {job.job_id} timed out after {job.job_timeout_seconds}s")
            return False, "JOB_TIMEOUT", f"Job exceeded time limit of {job.job_timeout_seconds}s"
            
        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {e}", exc_info=True)
            return False, "RENDER_FAILED", str(e)
        finally:
            self.current_job = None
    
    def should_retry(self, job: Job, error_code: Optional[str] = None) -> bool:
        """Determine if job should be retried."""
        # Non-retryable error codes
        non_retryable = [
            'INVALID_URL',
            'SSRF_BLOCKED',
            'HTTP_4XX',
            'CAPTCHA_DETECTED',
            'DOMAIN_WAIT_TIMEOUT'
        ]
        
        if error_code in non_retryable:
            return False
        
        return job.attempts < job.max_retries
    
    async def run(self):
        """Main worker loop."""
        # ... (initialization code) ...
        
        try:
            while self.running:
                try:
                    # Claim next job
                    # ... (claim logic) ...
                    
                    if not job:
                        # ... (wait logic) ...
                        continue
                    
                    # Process job
                    success, error_code, error_message = await self.process_job(job)
                    
                    # Update job status
                    with get_db_context() as db:
                        if success:
                            QueueService.complete_job(db, job.job_id, success=True)
                        else:
                            # Check if should retry
                            if self.should_retry(job, error_code):
                                logger.info(f"Requeuing job {job.job_id} for retry")
                                QueueService.requeue_job(db, job.job_id)
                            else:
                                logger.warning(f"Job {job.job_id} failed permanently: {error_code} - {error_message}")
                                QueueService.complete_job(
                                    db,
                                    job.job_id,
                                    success=False,
                                    error_code=error_code or 'RENDER_FAILED',
                                    error_message=error_message or 'Unknown error'
                                )
                
                except Exception as e:
                    logger.error(f"Error in worker loop: {e}", exc_info=True)
                    await asyncio.sleep(5)
                
                except Exception as e:
                    logger.error(f"Error in worker loop: {e}", exc_info=True)
                    await asyncio.sleep(5)
        
        finally:
            logger.info("Worker shutting down")
            await render_service.close()


async def main():
    """Entry point for worker."""
    worker = Worker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
