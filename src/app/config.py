"""Configuration management using pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Database
    sqlite_db_path: str = "./data/app.db"
    
    # Storage
    pdf_storage_path: str = "./data/pdfs"
    
    # Render
    default_render_mode: str = "print_to_pdf"
    
    # Timeouts (seconds)
    navigation_timeout_seconds: int = 45
    job_timeout_seconds: int = 120
    max_domain_wait_seconds: int = 600
    
    # Retry
    max_retries: int = 2
    
    # Cleanup (seconds)
    cleanup_interval_seconds: int = 1020
    cleanup_file_age_seconds: int = 1020
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Worker
    worker_poll_interval_seconds: int = 2
    
    # Logging
    log_level: str = "INFO"
    
    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        Path(self.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.pdf_storage_path).mkdir(parents=True, exist_ok=True)


settings = Settings()
