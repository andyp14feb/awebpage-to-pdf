"""Integration tests for queue service."""
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Job, JobStatus
from app.queue.service import QueueService


@pytest.fixture
def db_session():
    """Create in-memory database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestJobCreation:
    """Test job creation and deduplication."""
    
    def test_create_new_job(self, db_session):
        job, deduplicated = QueueService.create_job(
            db=db_session,
            url="https://example.com/test"
        )
        
        assert job.job_id is not None
        assert job.status == JobStatus.QUEUED.value
        assert deduplicated is False
    
    def test_deduplication_same_day(self, db_session):
        # Create first job
        job1, dedup1 = QueueService.create_job(
            db=db_session,
            url="https://example.com/test"
        )
        
        # Create second job with same URL
        job2, dedup2 = QueueService.create_job(
            db=db_session,
            url="https://example.com/test"
        )
        
        assert job1.job_id == job2.job_id
        assert dedup1 is False
        assert dedup2 is True
    
    def test_normalization_deduplication(self, db_session):
        # Create with trailing slash
        job1, _ = QueueService.create_job(
            db=db_session,
            url="https://example.com/test/"
        )
        
        # Create without trailing slash
        job2, dedup = QueueService.create_job(
            db=db_session,
            url="https://example.com/test"
        )
        
        assert job1.job_id == job2.job_id
        assert dedup is True


class TestJobClaiming:
    """Test job claiming and domain locking."""
    
    def test_claim_queued_job(self, db_session):
        # Create job
        job, _ = QueueService.create_job(
            db=db_session,
            url="https://example.com/test"
        )
        
        # Claim job
        claimed = QueueService.claim_next_job(db_session)
        
        assert claimed is not None
        assert claimed.job_id == job.job_id
        assert claimed.status == JobStatus.RUNNING.value
        assert claimed.attempts == 1
    
    def test_domain_lock_prevents_concurrent(self, db_session):
        # Create two jobs for same domain
        job1, _ = QueueService.create_job(
            db=db_session,
            url="https://example.com/page1"
        )
        job2, _ = QueueService.create_job(
            db=db_session,
            url="https://example.com/page2"
        )
        
        # Claim first job
        claimed1 = QueueService.claim_next_job(db_session)
        assert claimed1.job_id == job1.job_id
        
        # Try to claim second job - should be blocked by domain lock
        claimed2 = QueueService.claim_next_job(db_session)
        assert claimed2 is None
        
        # Complete first job
        QueueService.complete_job(db_session, job1.job_id, success=True)
        
        # Now second job should be claimable
        claimed3 = QueueService.claim_next_job(db_session)
        assert claimed3 is not None
        assert claimed3.job_id == job2.job_id


class TestJobCompletion:
    """Test job completion."""
    
    def test_complete_success(self, db_session):
        job, _ = QueueService.create_job(
            db=db_session,
            url="https://example.com/test"
        )
        
        claimed = QueueService.claim_next_job(db_session)
        QueueService.complete_job(db_session, claimed.job_id, success=True)
        
        completed = QueueService.get_job(db_session, job.job_id)
        assert completed.status == JobStatus.SUCCEEDED.value
        assert completed.finished_at is not None
    
    def test_complete_failure(self, db_session):
        job, _ = QueueService.create_job(
            db=db_session,
            url="https://example.com/test"
        )
        
        claimed = QueueService.claim_next_job(db_session)
        QueueService.complete_job(
            db_session,
            claimed.job_id,
            success=False,
            error_code="TEST_ERROR",
            error_message="Test error message"
        )
        
        completed = QueueService.get_job(db_session, job.job_id)
        assert completed.status == JobStatus.FAILED.value
        assert completed.error_code == "TEST_ERROR"
        assert completed.error_message == "Test error message"
