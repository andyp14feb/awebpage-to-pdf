"""Database models for the Webpage-to-PDF service."""
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, Integer, DateTime, Boolean, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class JobStatus(str, Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    WAITING_DOMAIN_LOCK = "waiting_domain_lock"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RenderMode(str, Enum):
    """Render mode enumeration."""
    PRINT_TO_PDF = "print_to_pdf"
    SCREENSHOT_TO_PDF = "screenshot_to_pdf"


class Job(Base):
    """Job model representing a PDF conversion job."""
    __tablename__ = "jobs"
    
    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    normalized_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    main_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=JobStatus.QUEUED.value, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Error tracking
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    # Configuration
    render_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    navigation_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    job_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_domain_wait_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Deduplication
    deduplicated: Mapped[bool] = mapped_column(Boolean, default=False)
    submission_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    
    # Metadata (optional)
    metadata_json: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    
    __table_args__ = (
        Index('idx_dedup', 'normalized_url', 'submission_date', unique=True),
        Index('idx_status_created', 'status', 'created_at'),
    )


class DomainLock(Base):
    """Domain lock model for serialization by main domain."""
    __tablename__ = "domain_locks"
    
    main_domain: Mapped[str] = mapped_column(String(255), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False)
    locked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    max_wait_seconds: Mapped[int] = mapped_column(Integer, nullable=False)


class WorkerHeartbeat(Base):
    """Worker heartbeat model for health monitoring."""
    __tablename__ = "worker_heartbeats"
    
    worker_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    current_job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
