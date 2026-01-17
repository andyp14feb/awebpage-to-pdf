"""Cleanup scheduler for removing old PDF files."""
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

from app.config import settings

logger = logging.getLogger(__name__)


class CleanupScheduler:
    """Scheduler for cleaning up old PDF files."""
    
    def __init__(self):
        self.running = False
    
    async def cleanup_old_files(self) -> None:
        """Remove PDF files older than configured age threshold."""
        pdf_dir = Path(settings.pdf_storage_path)
        
        if not pdf_dir.exists():
            logger.debug("PDF storage directory does not exist, skipping cleanup")
            return
        
        now = datetime.now(timezone.utc)
        age_threshold = timedelta(seconds=settings.cleanup_file_age_seconds)
        
        deleted_count = 0
        error_count = 0
        
        for pdf_file in pdf_dir.glob("*.pdf"):
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(pdf_file.stat().st_mtime, tz=timezone.utc)
                age = now - mtime
                
                if age > age_threshold:
                    pdf_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old PDF: {pdf_file.name} (age: {age.total_seconds()}s)")
            
            except Exception as e:
                error_count += 1
                logger.error(f"Error deleting {pdf_file.name}: {e}")
        
        if deleted_count > 0 or error_count > 0:
            logger.info(f"Cleanup completed: deleted {deleted_count} files, {error_count} errors")
    
    async def run(self) -> None:
        """Run cleanup scheduler loop."""
        logger.info(f"Starting cleanup scheduler (interval: {settings.cleanup_interval_seconds}s, age threshold: {settings.cleanup_file_age_seconds}s)")
        
        self.running = True
        
        while self.running:
            try:
                await self.cleanup_old_files()
            except Exception as e:
                logger.error(f"Error in cleanup scheduler: {e}", exc_info=True)
            
            # Wait for next interval
            await asyncio.sleep(settings.cleanup_interval_seconds)
    
    def stop(self) -> None:
        """Stop the cleanup scheduler."""
        self.running = False


# Global cleanup scheduler instance
cleanup_scheduler = CleanupScheduler()
