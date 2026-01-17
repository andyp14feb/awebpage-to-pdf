"""Queue service for job management."""
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import Job, DomainLock, JobStatus, RenderMode
from app.config import settings
from app.security.url_validator import normalize_url, validate_url_format, validate_ssrf
from app.utils.domain import extract_main_domain
import logging

logger = logging.getLogger(__name__)


class QueueService:
    """Service for managing job queue operations."""
    
    @staticmethod
    def create_job(
        db: Session,
        url: str,
        render_mode: Optional[str] = None,
        navigation_timeout_seconds: Optional[int] = None,
        job_timeout_seconds: Optional[int] = None,
        max_domain_wait_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[Job, bool]:
        """
        Create a new job or return existing deduplicated job.
        
        Returns:
            Tuple of (Job, deduplicated_flag)
        """
        # Validate URL
        validate_url_format(url)
        validate_ssrf(url)
        
        # Normalize URL
        normalized_url = normalize_url(url)
        
        # Extract main domain
        main_domain = extract_main_domain(url)
        
        # Get submission date (UTC)
        now = datetime.now(timezone.utc)
        submission_date = now.strftime("%Y-%m-%d")
        
        # Check for existing job (deduplication)
        existing_job = db.execute(
            select(Job).where(
                and_(
                    Job.normalized_url == normalized_url,
                    Job.submission_date == submission_date
                )
            )
        ).scalar_one_or_none()
        
        if existing_job:
            logger.info(f"Deduplicated job for URL: {normalized_url}, returning job_id: {existing_job.job_id}")
            return existing_job, True
        
        # Create new job
        job_id = str(uuid.uuid4())
        
        job = Job(
            job_id=job_id,
            normalized_url=normalized_url,
            main_domain=main_domain,
            status=JobStatus.QUEUED.value,
            attempts=0,
            created_at=now,
            render_mode=render_mode or settings.default_render_mode,
            navigation_timeout_seconds=navigation_timeout_seconds or settings.navigation_timeout_seconds,
            job_timeout_seconds=job_timeout_seconds or settings.job_timeout_seconds,
            max_domain_wait_seconds=max_domain_wait_seconds or settings.max_domain_wait_seconds,
            max_retries=max_retries or settings.max_retries,
            deduplicated=False,
            submission_date=submission_date,
            metadata_json=json.dumps(metadata) if metadata else None
        )
        
        try:
            db.add(job)
            db.commit()
            db.refresh(job)
            logger.info(f"Created new job: {job_id} for URL: {normalized_url}")
            return job, False
        except IntegrityError:
            # Race condition - another process created the same job
            db.rollback()
            existing_job = db.execute(
                select(Job).where(
                    and_(
                        Job.normalized_url == normalized_url,
                        Job.submission_date == submission_date
                    )
                )
            ).scalar_one_or_none()
            if existing_job:
                logger.info(f"Race condition detected, returning existing job: {existing_job.job_id}")
                return existing_job, True
            raise
    
    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return db.execute(
            select(Job).where(Job.job_id == job_id)
        ).scalar_one_or_none()
    
    @staticmethod
    def claim_next_job(db: Session) -> Optional[Job]:
        """
        Claim the next eligible job for processing.
        
        Returns:
            Job if available, None otherwise
        """
        now = datetime.now(timezone.utc)
        
        # Find next queued job
        job = db.execute(
            select(Job)
            .where(Job.status == JobStatus.QUEUED.value)
            .order_by(Job.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()
        
        if not job:
            # Check for jobs waiting on domain lock
            job = db.execute(
                select(Job)
                .where(Job.status == JobStatus.WAITING_DOMAIN_LOCK.value)
                .order_by(Job.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            ).scalar_one_or_none()
        
        if not job:
            return None
        
        # Check domain lock
        lock = db.execute(
            select(DomainLock).where(DomainLock.main_domain == job.main_domain)
        ).scalar_one_or_none()
        
        if lock:
            # Domain is locked by another job
            # Ensure created_at is timezone-aware for comparison
            created_at_utc = job.created_at.replace(tzinfo=timezone.utc) if job.created_at.tzinfo is None else job.created_at
            wait_duration = (now - created_at_utc).total_seconds()
            
            if wait_duration > job.max_domain_wait_seconds:
                # Timeout exceeded
                job.status = JobStatus.FAILED.value
                job.error_code = "DOMAIN_WAIT_TIMEOUT"
                job.error_message = f"Exceeded max domain wait time: {job.max_domain_wait_seconds}s"
                job.finished_at = now
                db.commit()
                logger.warning(f"Job {job.job_id} failed due to domain wait timeout")
                return None
            else:
                # Update to waiting state
                if job.status != JobStatus.WAITING_DOMAIN_LOCK.value:
                    job.status = JobStatus.WAITING_DOMAIN_LOCK.value
                    db.commit()
                logger.debug(f"Job {job.job_id} waiting for domain lock on {job.main_domain}")
                return None
        
        # Acquire domain lock
        new_lock = DomainLock(
            main_domain=job.main_domain,
            job_id=job.job_id,
            locked_at=now,
            max_wait_seconds=job.max_domain_wait_seconds
        )
        db.add(new_lock)
        
        # Update job status
        job.status = JobStatus.RUNNING.value
        job.started_at = now
        job.attempts += 1
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"Claimed job {job.job_id} for processing (attempt {job.attempts})")
        return job
    
    @staticmethod
    def complete_job(db: Session, job_id: str, success: bool, error_code: Optional[str] = None, error_message: Optional[str] = None) -> None:
        """Mark job as completed (succeeded or failed)."""
        job = QueueService.get_job(db, job_id)
        if not job:
            logger.error(f"Job {job_id} not found for completion")
            return
        
        now = datetime.now(timezone.utc)
        
        if success:
            job.status = JobStatus.SUCCEEDED.value
            job.error_code = None
            job.error_message = None
        else:
            job.status = JobStatus.FAILED.value
            job.error_code = error_code
            job.error_message = error_message
        
        job.finished_at = now
        
        # Release domain lock
        db.execute(
            DomainLock.__table__.delete().where(DomainLock.main_domain == job.main_domain)
        )
        
        db.commit()
        logger.info(f"Job {job_id} completed with status: {job.status}")
    
    @staticmethod
    def requeue_job(db: Session, job_id: str) -> None:
        """Requeue a job for retry."""
        job = QueueService.get_job(db, job_id)
        if not job:
            logger.error(f"Job {job_id} not found for requeue")
            return
        
        # Release domain lock
        db.execute(
            DomainLock.__table__.delete().where(DomainLock.main_domain == job.main_domain)
        )
        
        # Reset to queued
        job.status = JobStatus.QUEUED.value
        job.started_at = None
        
        db.commit()
        logger.info(f"Job {job_id} requeued for retry (attempt {job.attempts}/{job.max_retries})")
