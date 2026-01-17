"""API schemas for request/response models."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from app.models import RenderMode


class JobSubmitRequest(BaseModel):
    """Request model for job submission."""
    url: str = Field(..., description="URL to convert to PDF")
    render_mode: Optional[str] = Field(None, description="Render mode: print_to_pdf or screenshot_to_pdf")
    max_domain_wait_seconds: Optional[int] = Field(None, ge=10, le=3600, description="Max wait for domain lock")
    navigation_timeout_seconds: Optional[int] = Field(None, ge=5, le=300, description="Page navigation timeout")
    job_timeout_seconds: Optional[int] = Field(None, ge=10, le=600, description="Total job timeout")
    max_retries: Optional[int] = Field(None, ge=0, le=5, description="Maximum retry attempts")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")
    
    @field_validator('render_mode')
    @classmethod
    def validate_render_mode(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in [RenderMode.PRINT_TO_PDF.value, RenderMode.SCREENSHOT_TO_PDF.value]:
            raise ValueError(f"render_mode must be one of: {RenderMode.PRINT_TO_PDF.value}, {RenderMode.SCREENSHOT_TO_PDF.value}")
        return v


class JobSubmitResponse(BaseModel):
    """Response model for job submission."""
    job_id: str
    status: str
    deduplicated: bool


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str
    attempts: int
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_code: Optional[str]
    error_message: Optional[str]
    deduplicated: bool
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
