"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Request Schemas ──────────────────────────────────────────────────────────

class ProcessDocumentRequest(BaseModel):
    """Request to process all pages of a PDF."""
    pdf_id: str


class ProcessPageRequest(BaseModel):
    """Request to process a specific page of a PDF."""
    pdf_id: str
    page_number: int = Field(..., ge=0, description="Zero-indexed page number")


# ─── Response Schemas ─────────────────────────────────────────────────────────

class PagePreview(BaseModel):
    """Preview information for a single PDF page."""
    page_number: int
    width: int
    height: int
    preview_url: str


class UploadResponse(BaseModel):
    """Response after uploading a PDF."""
    pdf_id: str
    total_pages: int
    pages: List[PagePreview]


class SlotResult(BaseModel):
    """A single detected parking slot."""
    slot_id: str
    parking_type: str
    confidence: float
    bbox: List[float]  # [x0, y0, x1, y1]


class PageResult(BaseModel):
    """Processing result for a single page."""
    page_number: int
    total_slots: int
    slots: List[SlotResult]
    result_image_url: Optional[str] = None
    summary: dict = Field(default_factory=dict)  # e.g. {"type_abc": 5, "type_def": 3}


class ProcessResult(BaseModel):
    """Full processing result for all processed pages."""
    pdf_id: str
    pages: List[PageResult]


class ProgressResponse(BaseModel):
    """Progress update for a background task."""
    task_id: str
    status: TaskStatus
    progress: float = Field(0.0, ge=0.0, le=100.0)
    message: str = ""
    result: Optional[ProcessResult] = None
